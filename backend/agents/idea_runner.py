"""
Core runner for Research Idea CLAW — multi-expert internal debate + arbitrator verdict.

Flow per user round:
  1. Internal debate loop (internal_rounds sub-rounds):
     - For each sub-round: 3 experts speak sequentially, each seeing all prior debate msgs
     - SSE events carry `internal_round` field to distinguish sub-rounds
  2. Arbitrator: aggregates all debate → outputs verdict + [REFINED_QUESTION]...[/REFINED_QUESTION]
  3. round_complete event carries `refined_question` field → frontend auto-fills input box
  4. Block on answer_queue for user-revised question or 'done' signal
  5. Loop to next round or finish

Queues (same as before):
  - event_queue: producer side (runner → SSE endpoint)
  - answer_queue: consumer side (runner blocks waiting for user revision)
"""
import queue
import re
from datetime import datetime

from llm.openrouter_client import OpenRouterClient
from llm.semantic_scholar import search_papers, format_papers_for_prompt
from models.idea_session import IdeaSession
from agents.idea_prompts import (
    SAFETY_ENGINEER_SYSTEM_PROMPT,
    SAFETY_PROFESSOR_SYSTEM_PROMPT,
    NASA_EXPERT_SYSTEM_PROMPT,
    ARBITRATOR_SYSTEM_PROMPT,
    AGENT_USER_TEMPLATE,
    ARBITRATOR_USER_TEMPLATE,
)

_client = OpenRouterClient()

AGENTS = [
    ("safety_engineer",  "系统安全工程师", SAFETY_ENGINEER_SYSTEM_PROMPT),
    ("safety_professor", "安全领域教授",   SAFETY_PROFESSOR_SYSTEM_PROMPT),
    ("nasa_expert",      "NASA技术专家",   NASA_EXPERT_SYSTEM_PROMPT),
]

REFINED_QUESTION_RE = re.compile(
    r"\[REFINED_QUESTION\](.*?)\[/REFINED_QUESTION\]", re.DOTALL
)
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


def _build_internal_debate_history(
    debate_msgs: list[tuple[int, str, str, str]]
) -> str:
    """Format all debate messages accumulated so far in this user round.
    Each item is (sub_round, agent_key, agent_role, content).
    """
    if not debate_msgs:
        return "（你是本轮第一位发言的专家）"
    lines = []
    for sub_round, agent_key, role, content in debate_msgs:
        lines.append(f"**[辩论第{sub_round}轮] {role}（{agent_key}）**:\n{content}\n")
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
    refined_question = ""
    try:
        session = IdeaSession.load(session_id)
        agent_config = session.agent_config
        internal_rounds = getattr(session, "internal_rounds", 3)

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

            # Accumulates ALL debate messages in this user round:
            # (sub_round, agent_key, agent_role, content)
            all_debate_msgs: list[tuple[int, str, str, str]] = []

            user_context_block = (
                f"**补充背景**：{session.user_context}" if session.user_context else ""
            )
            discussion_history = _build_discussion_history(session.discussions, round_num)

            # -----------------------------------------------------------
            # Internal debate loop: internal_rounds sub-rounds
            # -----------------------------------------------------------
            for sub_round in range(1, internal_rounds + 1):
                _push(event_queue, _make_event(
                    "internal_round_start", "system", "系统",
                    f"内部辩论第 {sub_round} / {internal_rounds} 小轮",
                    phase="discussing", round=round_num, internal_round=sub_round
                ))

                for agent_key, agent_role, system_prompt in AGENTS:
                    model = agent_config.get(agent_key, DEFAULT_MODEL)

                    _push(event_queue, _make_event(
                        "start", agent_key, agent_role,
                        f"{agent_role} 开始发言...",
                        phase="discussing", round=round_num, internal_round=sub_round
                    ))

                    debate_history_text = _build_internal_debate_history(all_debate_msgs)
                    user_prompt = AGENT_USER_TEMPLATE.format(
                        research_question=session.research_question,
                        user_context_block=user_context_block,
                        search_results=search_text,
                        discussion_history=discussion_history,
                        internal_debate_history=debate_history_text,
                    )

                    content = _client.chat(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user",   "content": user_prompt},
                        ],
                        temperature=0.75,
                        max_tokens=2048,
                    )

                    session.discussions.append({
                        "round": round_num,
                        "internal_round": sub_round,
                        "agent": agent_key,
                        "role": agent_role,
                        "content": content,
                        "timestamp": _now(),
                    })
                    session.save()
                    all_debate_msgs.append((sub_round, agent_key, agent_role, content))

                    _push(event_queue, _make_event(
                        "complete", agent_key, agent_role, content,
                        phase="discussing", round=round_num, internal_round=sub_round
                    ))

            # -----------------------------------------------------------
            # Arbitrator — synthesize debate and output verdict + refined question
            # -----------------------------------------------------------
            arbitrator_model = agent_config.get("arbitrator", DEFAULT_MODEL)
            _push(event_queue, _make_event(
                "start", "arbitrator", "仲裁者",
                "正在综合辩论结果，给出仲裁结论...",
                phase="summarizing", round=round_num
            ))

            debate_content = "\n\n".join(
                f"**[辩论第{sr}轮] {role}（{ak}）**:\n{body}"
                for sr, ak, role, body in all_debate_msgs
            )
            arbitrator_prompt = ARBITRATOR_USER_TEMPLATE.format(
                research_question=session.research_question,
                user_context_block=user_context_block,
                search_results=search_text,
                discussion_history=discussion_history,
                round_num=round_num,
                debate_content=debate_content,
            )
            arbitrator_content = _client.chat(
                model=arbitrator_model,
                messages=[
                    {"role": "system", "content": ARBITRATOR_SYSTEM_PROMPT},
                    {"role": "user",   "content": arbitrator_prompt},
                ],
                temperature=0.6,
                max_tokens=4096,
            )

            # Extract and strip the [REFINED_QUESTION] marker
            refined_match = REFINED_QUESTION_RE.search(arbitrator_content)
            refined_question = refined_match.group(1).strip() if refined_match else ""
            display_arbitrator = REFINED_QUESTION_RE.sub("", arbitrator_content).strip()

            session.summaries.append({
                "round": round_num,
                "content": arbitrator_content,
                "refined_question": refined_question,
                "timestamp": _now(),
            })
            session.save()

            _push(event_queue, _make_event(
                "complete", "arbitrator", "仲裁者", display_arbitrator,
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
                    f"第 {round_num} 轮讨论完成，请修改研究问题后继续或结束讨论",
                    phase="waiting_for_revision", round=round_num,
                    refined_question=refined_question,
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
                    f"已收到修改后的研究问题，开始第 {round_num + 1} 轮讨论",
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
