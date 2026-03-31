"""
Core runner for Research Idea CLAW discussions.
Uses an imperative loop (not LangGraph) to support real-time interrupts.

ROUND-TABLE MODE: Experts speak sequentially within each round.
Each expert can see what the previous experts said in the current round.

Flow per round:
  1. For each of 3 agents *sequentially*: call LLM (with current-round context)
     → detect [ASK_USER] → block on answer_queue if needed
  2. Summarizer: aggregate expert outputs → produce round summary
  3. Push round_complete event → set status=waiting_for_revision
  4. Block on answer_queue for user-revised idea or 'done' signal
  5. Loop to next round or finish

PAUSE PROTOCOL:
  - event_queue: producer side (runner → SSE endpoint reads this)
  - answer_queue: consumer side (runner blocks here waiting for user input)
  Both queues are put in _idea_queues[session_id] = (event_q, answer_q)
"""
import queue
import re
import threading
from datetime import datetime

from llm.openrouter_client import OpenRouterClient
from llm.semantic_scholar import search_papers, format_papers_for_prompt
from models.idea_session import IdeaSession
from agents.idea_prompts import (
    INNOVATION_SYSTEM_PROMPT,
    FEASIBILITY_SYSTEM_PROMPT,
    METHODOLOGY_SYSTEM_PROMPT,
    SUMMARIZER_SYSTEM_PROMPT,
    AGENT_USER_TEMPLATE,
    SUMMARIZER_USER_TEMPLATE,
)

_client = OpenRouterClient()

AGENTS = [
    ("innovation_expert",   "创新性评估者",   INNOVATION_SYSTEM_PROMPT),
    ("feasibility_analyst", "技术可行性分析师", FEASIBILITY_SYSTEM_PROMPT),
    ("methodology_expert",  "方法论专家",     METHODOLOGY_SYSTEM_PROMPT),
]

ASK_USER_RE = re.compile(r"\[ASK_USER\](.*?)\[/ASK_USER\]", re.DOTALL)
DEFAULT_MODEL = "deepseek/deepseek-chat"


def _now() -> str:
    return datetime.utcnow().isoformat()


def _push(q: queue.Queue, event: dict):
    q.put(event)


def _make_event(event_type: str, agent: str, role: str, content: str, **extra) -> dict:
    return {
        "type": event_type,
        "agent": agent,
        "role": role,
        "content": content,
        "timestamp": _now(),
        **extra,
    }


def _build_discussion_history(discussions: list, round_num: int | None = None) -> str:
    """Format previous rounds' discussions for prompt context."""
    if not discussions:
        return "（本轮是第一轮讨论）"
    lines = []
    for d in discussions:
        if round_num is not None and d.get("round") >= round_num:
            continue
        lines.append(f"**第{d['round']}轮 - {d['role']}（{d['agent']}）**:\n{d['content']}\n")
    return "\n".join(lines) if lines else "（暂无历史讨论）"


def _build_current_round_messages(round_messages: list[tuple[str, str, str]]) -> str:
    """Format messages from experts who have already spoken in this round.
    Each item is (agent_key, agent_role, content).
    """
    if not round_messages:
        return "（你是本轮第一位发言的专家）"
    lines = []
    for _agent_key, role, content in round_messages:
        lines.append(f"### {role} 的发言\n\n{content}\n")
    return "\n".join(lines)


def _build_user_answers_block(user_answers: list, round_num: int) -> str:
    answers = [a for a in user_answers if a.get("round") == round_num]
    if not answers:
        return ""
    lines = ["## 用户补充回答"]
    for a in answers:
        lines.append(f"**{a['role']}提问**：{a['question']}\n**用户回答**：{a['answer']}\n")
    return "\n".join(lines)


def run_idea_discussion(
    session_id: str,
    event_queue: queue.Queue,
    answer_queue: queue.Queue,
):
    """
    Main runner. Designed to be called in a background thread.
    Loads session from disk at the start and saves incrementally.
    """
    try:
        session = IdeaSession.load(session_id)
        agent_config = session.agent_config

        # ---------------------------------------------------------------
        # Step 0: Search for relevant papers
        # ---------------------------------------------------------------
        _push(event_queue, _make_event(
            "start", "system", "系统", "正在搜索相关论文...", phase="preparing"
        ))
        try:
            papers = search_papers(session.research_question, limit=8)
            session.search_results = papers
            session.save()
        except Exception as e:
            papers = []
            _push(event_queue, _make_event(
                "info", "system", "系统",
                f"论文搜索失败（将继续讨论）：{e}", phase="preparing"
            ))

        search_text = format_papers_for_prompt(papers)
        _push(event_queue, _make_event(
            "complete", "system", "系统",
            f"找到 {len(papers)} 篇相关论文", phase="preparing",
            search_results=papers,
        ))

        # ---------------------------------------------------------------
        # Main discussion loop
        # ---------------------------------------------------------------
        for round_num in range(1, session.max_rounds + 1):
            session.current_round = round_num
            session.status = "discussing"
            session.save()

            _push(event_queue, _make_event(
                "round_start", "system", "系统",
                f"开始第 {round_num} 轮讨论", phase="discussing", round=round_num
            ))

            round_expert_outputs: list[str] = []
            # Track messages from experts who already spoke in this round
            current_round_msgs: list[tuple[str, str, str]] = []

            # -----------------------------------------------------------
            # Each expert agent — SEQUENTIAL round-table order
            # -----------------------------------------------------------
            for agent_key, agent_role, system_prompt in AGENTS:
                model = agent_config.get(agent_key, DEFAULT_MODEL)

                _push(event_queue, _make_event(
                    "start", agent_key, agent_role, f"{agent_role} 开始分析...",
                    phase="discussing", round=round_num
                ))

                user_context_block = (
                    f"**补充背景**：{session.user_context}" if session.user_context
                    else ""
                )
                discussion_history = _build_discussion_history(session.discussions, round_num)
                user_answers_block = _build_user_answers_block(session.user_answers, round_num)
                current_round_text = _build_current_round_messages(current_round_msgs)

                user_prompt = AGENT_USER_TEMPLATE.format(
                    research_question=session.research_question,
                    user_context_block=user_context_block,
                    search_results=search_text,
                    discussion_history=discussion_history,
                    current_round_messages=current_round_text,
                    user_answers_block=user_answers_block,
                )

                content = _client.chat(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=4096,
                )

                # Detect [ASK_USER] marker
                ask_match = ASK_USER_RE.search(content)
                if ask_match:
                    question_text = ask_match.group(1).strip()
                    # Strip the marker from displayed content
                    display_content = ASK_USER_RE.sub("", content).strip()

                    # Save partial content
                    if display_content:
                        session.discussions.append({
                            "round": round_num, "agent": agent_key,
                            "role": agent_role, "content": display_content,
                            "timestamp": _now(),
                        })
                        session.save()
                        _push(event_queue, _make_event(
                            "partial", agent_key, agent_role, display_content,
                            phase="discussing", round=round_num
                        ))

                    # Pause: ask user
                    session.status = "waiting_for_input"
                    session.pending_question = question_text
                    session.pending_question_agent = agent_key
                    session.save()

                    _push(event_queue, _make_event(
                        "question", agent_key, agent_role, question_text,
                        phase="waiting_for_input", round=round_num
                    ))

                    # Block until user answers (1 hour timeout)
                    try:
                        answer = answer_queue.get(timeout=3600)
                    except queue.Empty:
                        raise RuntimeError("等待用户回答超时（1小时）")

                    if answer is None:
                        raise RuntimeError("用户取消了讨论")

                    # Record answer
                    session.user_answers.append({
                        "round": round_num, "agent": agent_key, "role": agent_role,
                        "question": question_text, "answer": answer,
                        "timestamp": _now(),
                    })
                    session.status = "discussing"
                    session.pending_question = ""
                    session.save()

                    _push(event_queue, _make_event(
                        "answer_received", agent_key, agent_role,
                        answer, phase="discussing", round=round_num
                    ))

                    # Re-call with user answer included
                    updated_answers_block = _build_user_answers_block(session.user_answers, round_num)
                    user_prompt_retry = AGENT_USER_TEMPLATE.format(
                        research_question=session.research_question,
                        user_context_block=user_context_block,
                        search_results=search_text,
                        discussion_history=discussion_history,
                        current_round_messages=current_round_text,
                        user_answers_block=updated_answers_block,
                    )
                    content = _client.chat(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user",   "content": user_prompt_retry},
                        ],
                        temperature=0.7,
                        max_tokens=4096,
                    )
                    content = ASK_USER_RE.sub("", content).strip()

                # Save expert output
                session.discussions.append({
                    "round": round_num, "agent": agent_key,
                    "role": agent_role, "content": content,
                    "timestamp": _now(),
                })
                session.save()
                round_expert_outputs.append(f"### {agent_role}\n\n{content}")
                # Track for next expert in this round
                current_round_msgs.append((agent_key, agent_role, content))

                _push(event_queue, _make_event(
                    "complete", agent_key, agent_role, content,
                    phase="discussing", round=round_num
                ))

            # -----------------------------------------------------------
            # Summarizer
            # -----------------------------------------------------------
            summarizer_model = agent_config.get("summarizer", DEFAULT_MODEL)
            _push(event_queue, _make_event(
                "start", "summarizer", "研究顾问", "正在综合各专家意见...",
                phase="summarizing", round=round_num
            ))

            user_context_block = (
                f"**补充背景**：{session.user_context}" if session.user_context else ""
            )
            summarizer_prompt = SUMMARIZER_USER_TEMPLATE.format(
                research_question=session.research_question,
                user_context_block=user_context_block,
                round_num=round_num,
                expert_discussions="\n\n".join(round_expert_outputs),
            )
            summary_content = _client.chat(
                model=summarizer_model,
                messages=[
                    {"role": "system", "content": SUMMARIZER_SYSTEM_PROMPT},
                    {"role": "user",   "content": summarizer_prompt},
                ],
                temperature=0.6,
                max_tokens=4096,
            )
            session.summaries.append({
                "round": round_num, "content": summary_content, "timestamp": _now()
            })
            session.save()

            _push(event_queue, _make_event(
                "complete", "summarizer", "研究顾问", summary_content,
                phase="summarizing", round=round_num
            ))

            # -----------------------------------------------------------
            # End of round: wait for user revision or finish
            # -----------------------------------------------------------
            if round_num < session.max_rounds:
                session.status = "waiting_for_revision"
                session.save()
                _push(event_queue, _make_event(
                    "round_complete", "system", "系统",
                    f"第 {round_num} 轮讨论完成，请修改研究想法后继续或结束讨论",
                    phase="waiting_for_revision", round=round_num
                ))

                # Block for user to revise idea or signal done
                try:
                    revision = answer_queue.get(timeout=3600)
                except queue.Empty:
                    raise RuntimeError("等待用户修改超时（1小时）")

                if revision is None or revision == "__DONE__":
                    break   # User chose to finish early

                # revision is a dict: {"research_question": ..., "user_context": ...}
                if isinstance(revision, dict):
                    if revision.get("research_question"):
                        session.research_question = revision["research_question"]
                    if revision.get("user_context") is not None:
                        session.user_context = revision["user_context"]
                    session.save()

                _push(event_queue, _make_event(
                    "revision_received", "system", "系统",
                    f"已收到修改后的研究想法，开始第 {round_num + 1} 轮讨论",
                    phase="discussing", round=round_num + 1
                ))
            else:
                # Last round finished
                break

        # ---------------------------------------------------------------
        # Complete
        # ---------------------------------------------------------------
        session.status = "complete"
        session.save()
        _push(event_queue, _make_event(
            "complete", "system", "系统", "讨论已完成！",
            phase="complete"
        ))

    except Exception as e:
        try:
            session = IdeaSession.load(session_id)
            session.status = "error"
            session.error = str(e)
            session.save()
        except Exception:
            pass
        _push(event_queue, _make_event(
            "error", "system", "系统", f"讨论出错：{e}", phase="error"
        ))
    finally:
        event_queue.put(None)  # sentinel — close SSE stream
