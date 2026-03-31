import json
import queue
import threading
import uuid

from flask import Blueprint, Response, jsonify, request

from agents.idea_runner import run_idea_discussion
from config import AVAILABLE_MODELS
from models.idea_session import IdeaSession

idea_bp = Blueprint("idea", __name__, url_prefix="/api/idea")

# session_id -> (event_queue, answer_queue)
_idea_queues: dict[str, tuple[queue.Queue, queue.Queue]] = {}

_DEFAULT_IDEA_MODELS = {
    "innovation_expert": "deepseek/deepseek-chat",
    "feasibility_analyst": "deepseek/deepseek-chat",
    "methodology_expert": "deepseek/deepseek-chat",
    "summarizer": "deepseek/deepseek-chat",
}


# ---------------------------------------------------------------------------
# Start idea discussion
# ---------------------------------------------------------------------------
@idea_bp.route("/start", methods=["POST"])
def start_idea():
    body = request.get_json(silent=True) or {}
    research_question = (body.get("research_question") or "").strip()
    if not research_question:
        return jsonify({"error": "research_question 不能为空"}), 400

    user_context = (body.get("user_context") or "").strip()
    agent_config = body.get("agent_config", _DEFAULT_IDEA_MODELS.copy())
    max_rounds = int(body.get("max_rounds", 3))

    session_id = str(uuid.uuid4())
    session = IdeaSession(
        session_id=session_id,
        research_question=research_question,
        user_context=user_context,
        agent_config=agent_config,
        max_rounds=max_rounds,
    )
    session.save()

    event_q: queue.Queue = queue.Queue()
    answer_q: queue.Queue = queue.Queue()
    _idea_queues[session_id] = (event_q, answer_q)

    threading.Thread(
        target=run_idea_discussion,
        args=(session_id, event_q, answer_q),
        daemon=True,
    ).start()

    return jsonify({"session_id": session_id})


# ---------------------------------------------------------------------------
# SSE stream
# ---------------------------------------------------------------------------
@idea_bp.route("/sessions/<session_id>/stream")
def stream_idea(session_id: str):
    if session_id not in _idea_queues:
        try:
            session = IdeaSession.load(session_id)
            if session.status == "complete":
                def _finished():
                    yield f"data: {json.dumps({'type': 'complete', 'phase': 'complete', 'agent': 'system', 'content': '讨论已完成'}, ensure_ascii=False)}\n\n"
                return Response(_finished(), mimetype="text/event-stream")
        except FileNotFoundError:
            pass
        return jsonify({"error": "会话不存在或未启动"}), 404

    event_q, _ = _idea_queues[session_id]

    def generate():
        while True:
            try:
                event = event_q.get(timeout=30)
            except queue.Empty:
                yield ": keepalive\n\n"
                continue

            if event is None:
                yield f"data: {json.dumps({'type': 'complete', 'phase': 'complete', 'agent': 'system', 'content': '所有讨论流程已完成'}, ensure_ascii=False)}\n\n"
                _idea_queues.pop(session_id, None)
                break
            else:
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Submit answer to agent's [ASK_USER] question
# ---------------------------------------------------------------------------
@idea_bp.route("/sessions/<session_id>/answer", methods=["POST"])
def submit_answer(session_id: str):
    if session_id not in _idea_queues:
        return jsonify({"error": "会话不存在或未启动"}), 404

    body = request.get_json(silent=True) or {}
    answer = (body.get("answer") or "").strip()
    if not answer:
        return jsonify({"error": "answer 不能为空"}), 400

    _, answer_q = _idea_queues[session_id]
    answer_q.put(answer)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Submit revision (continue with updated research question)
# ---------------------------------------------------------------------------
@idea_bp.route("/sessions/<session_id>/revise", methods=["POST"])
def submit_revision(session_id: str):
    if session_id not in _idea_queues:
        return jsonify({"error": "会话不存在或未启动"}), 404

    body = request.get_json(silent=True) or {}
    research_question = (body.get("research_question") or "").strip()
    user_context = (body.get("user_context") or "").strip()

    _, answer_q = _idea_queues[session_id]
    answer_q.put({
        "research_question": research_question,
        "user_context": user_context,
    })
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Finish early (end discussion without more rounds)
# ---------------------------------------------------------------------------
@idea_bp.route("/sessions/<session_id>/finish", methods=["POST"])
def finish_early(session_id: str):
    if session_id not in _idea_queues:
        return jsonify({"error": "会话不存在或未启动"}), 404

    _, answer_q = _idea_queues[session_id]
    answer_q.put("__DONE__")
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------
@idea_bp.route("/sessions/<session_id>/cancel", methods=["POST"])
def cancel_idea(session_id: str):
    if session_id not in _idea_queues:
        return jsonify({"error": "会话不存在或未启动"}), 404

    _, answer_q = _idea_queues[session_id]
    answer_q.put(None)
    _idea_queues.pop(session_id, None)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Get full results
# ---------------------------------------------------------------------------
@idea_bp.route("/sessions/<session_id>/results")
def get_idea_results(session_id: str):
    try:
        session = IdeaSession.load(session_id)
    except FileNotFoundError:
        return jsonify({"error": "会话不存在"}), 404

    from dataclasses import asdict
    return jsonify(asdict(session))


# ---------------------------------------------------------------------------
# Download discussion as Markdown
# ---------------------------------------------------------------------------
@idea_bp.route("/sessions/<session_id>/download")
def download_idea_markdown(session_id: str):
    try:
        session = IdeaSession.load(session_id)
    except FileNotFoundError:
        return jsonify({"error": "会话不存在"}), 404

    lines: list[str] = []
    lines.append(f"# 研究想法圆桌讨论记录\n")
    lines.append(f"**研究问题**：{session.research_question}\n")
    if session.user_context:
        lines.append(f"**背景说明**：{session.user_context}\n")
    lines.append(f"**讨论轮数**：{session.current_round} / {session.max_rounds}\n")
    lines.append(f"**状态**：{session.status}\n")
    lines.append("---\n")

    # Search results
    if session.search_results:
        lines.append("## 相关论文\n")
        for i, paper in enumerate(session.search_results, 1):
            title = paper.get("title", "未知")
            year = paper.get("year", "")
            url = paper.get("url", "")
            authors = ", ".join(paper.get("authors", [])[:3])
            citation_count = paper.get("citationCount", "")
            line = f"{i}. **{title}**"
            if authors:
                line += f" — {authors}"
            if year:
                line += f" ({year})"
            if citation_count:
                line += f" [引用: {citation_count}]"
            if url:
                line += f"  \n   {url}"
            lines.append(line)
        lines.append("\n---\n")

    # Group discussions by round
    max_round = max((d.get("round", 1) for d in session.discussions), default=0)
    for r in range(1, max_round + 1):
        lines.append(f"## 第 {r} 轮圆桌讨论\n")

        # Expert discussions for this round
        round_discussions = [d for d in session.discussions if d.get("round") == r]
        for d in round_discussions:
            lines.append(f"### {d['role']}（{d['agent']}）\n")
            lines.append(d["content"])
            lines.append("")

        # User answers for this round
        round_answers = [a for a in session.user_answers if a.get("round") == r]
        if round_answers:
            lines.append("### 用户补充回答\n")
            for a in round_answers:
                lines.append(f"**{a['role']}提问**：{a['question']}")
                lines.append(f"**用户回答**：{a['answer']}\n")

        # Summary for this round
        round_summaries = [s for s in session.summaries if s.get("round") == r]
        if round_summaries:
            lines.append("### 本轮总结（研究顾问）\n")
            lines.append(round_summaries[0]["content"])
            lines.append("")

        lines.append("---\n")

    md_content = "\n".join(lines)
    filename = f"idea_discussion_{session_id[:8]}.md"

    return Response(
        md_content,
        mimetype="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


# ---------------------------------------------------------------------------
# List available models (reuse existing config)
# ---------------------------------------------------------------------------
@idea_bp.route("/models")
def list_models():
    return jsonify({"models": AVAILABLE_MODELS})
