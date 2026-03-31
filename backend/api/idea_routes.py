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
# List available models (reuse existing config)
# ---------------------------------------------------------------------------
@idea_bp.route("/models")
def list_models():
    return jsonify({"models": AVAILABLE_MODELS})
