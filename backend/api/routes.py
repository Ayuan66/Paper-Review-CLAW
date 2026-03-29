import base64
import json
import os
import queue
import threading
import uuid
from datetime import datetime

from flask import Blueprint, Response, jsonify, request, send_file

from config import (
    AGENT_ROLES,
    AVAILABLE_MODELS,
    DEFAULT_MODELS,
    MAX_AUTHOR_ITERATIONS,
    UPLOADS_DIR,
    VENUES,
)
from graph.workflow import build_review_graph
from llm.pdf_extractor import extract_from_base64
from models.review_session import ReviewSession

api_bp = Blueprint("api", __name__, url_prefix="/api")

# session_id -> queue.Queue for SSE streaming
_session_queues: dict[str, queue.Queue] = {}


# ---------------------------------------------------------------------------
# Upload PDF
# ---------------------------------------------------------------------------
@api_bp.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "未找到文件字段 'file'"}), 400

    file = request.files["file"]
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "请上传 PDF 文件"}), 400

    session_id = str(uuid.uuid4())
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    save_path = os.path.join(UPLOADS_DIR, f"{session_id}.pdf")
    file.save(save_path)

    session = ReviewSession(
        session_id=session_id,
        pdf_filename=file.filename,
        pdf_path=save_path,
        agent_config=DEFAULT_MODELS.copy(),
    )
    session.save()

    return jsonify({"session_id": session_id, "filename": file.filename})


# ---------------------------------------------------------------------------
# Start review process
# ---------------------------------------------------------------------------
@api_bp.route("/sessions/<session_id>/start", methods=["POST"])
def start_review(session_id: str):
    try:
        session = ReviewSession.load(session_id)
    except FileNotFoundError:
        return jsonify({"error": "会话不存在"}), 404

    if session.status not in ("created", "error"):
        return jsonify({"error": f"会话已处于 {session.status} 状态，无法重新启动"}), 400

    body = request.get_json(silent=True) or {}
    agent_config = body.get("agent_config", DEFAULT_MODELS.copy())
    max_iterations = int(body.get("max_iterations", MAX_AUTHOR_ITERATIONS))
    venue = body.get("venue", "")  # e.g. "ICSE", "TSE", or ""

    session.agent_config = agent_config
    session.status = "reviewing"
    session.save()

    # Read PDF, base64-encode, extract text + render page images
    with open(session.pdf_path, "rb") as f:
        pdf_bytes = f.read()
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    _pdf_bytes, pdf_text, page_images = extract_from_base64(pdf_base64)

    initial_state = {
        "session_id": session_id,
        "pdf_base64": pdf_base64,
        "pdf_filename": session.pdf_filename,
        "pdf_text": pdf_text,
        "pdf_page_images": page_images,
        "agent_config": agent_config,
        "venue": venue,
        "venue_context": "",  # filled by prepare_node
        "reviews": [],
        "editor_summary": "",
        "author_discussions": [],
        "author_iteration": 0,
        "max_author_iterations": max_iterations,
        "authors_reached_consensus": False,
        "final_revision_markdown": "",
        "current_phase": "reviewing",
        "progress_events": [],
    }

    q: queue.Queue = queue.Queue()
    _session_queues[session_id] = q

    thread = threading.Thread(
        target=_run_workflow,
        args=(session_id, initial_state, q),
        daemon=True,
    )
    thread.start()

    return jsonify({"status": "started"})


# ---------------------------------------------------------------------------
# SSE progress stream
# ---------------------------------------------------------------------------
@api_bp.route("/sessions/<session_id>/stream")
def stream_progress(session_id: str):
    if session_id not in _session_queues:
        # Workflow may have already finished; check session status
        try:
            session = ReviewSession.load(session_id)
            if session.status == "complete":
                def finished_gen():
                    yield f"data: {json.dumps({'phase': 'complete', 'agent': 'system', 'content': '评审已完成'})}\n\n"
                return Response(finished_gen(), mimetype="text/event-stream")
        except FileNotFoundError:
            pass
        return jsonify({"error": "会话不存在或未启动"}), 404

    q = _session_queues[session_id]

    def generate():
        while True:
            try:
                event = q.get(timeout=30)
            except queue.Empty:
                # Send keepalive comment
                yield ": keepalive\n\n"
                continue

            if event is None:
                # Workflow complete sentinel
                yield f"data: {json.dumps({'phase': 'complete', 'agent': 'system', 'content': '所有评审流程已完成'})}\n\n"
                _session_queues.pop(session_id, None)
                break
            else:
                # Strip full content from SSE to keep events lightweight.
                # Frontend fetches full content via /results.
                slim = {k: v for k, v in event.items() if k != "content"}
                slim["preview"] = (event.get("content") or "")[:120]
                yield f"data: {json.dumps(slim, ensure_ascii=False)}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Cancel / reset session
# ---------------------------------------------------------------------------
@api_bp.route("/sessions/<session_id>/cancel", methods=["POST"])
def cancel_review(session_id: str):
    # Unblock the SSE stream so frontend stops waiting
    q = _session_queues.pop(session_id, None)
    if q:
        q.put(None)  # send sentinel to end SSE stream
    try:
        session = ReviewSession.load(session_id)
        if session.status not in ("complete",):
            session.status = "error"
            session.error = "用户手动取消"
            session.save()
    except FileNotFoundError:
        pass
    return jsonify({"status": "cancelled"})


# ---------------------------------------------------------------------------
# Get status
# ---------------------------------------------------------------------------
@api_bp.route("/sessions/<session_id>/status")
def get_status(session_id: str):
    try:
        session = ReviewSession.load(session_id)
    except FileNotFoundError:
        return jsonify({"error": "会话不存在"}), 404

    phase_progress = {
        "created": 0,
        "reviewing": 20,
        "editing": 50,
        "discussing": 70,
        "complete": 100,
        "error": -1,
    }
    return jsonify({
        "status": session.status,
        "progress": phase_progress.get(session.status, 0),
    })


# ---------------------------------------------------------------------------
# Get results
# ---------------------------------------------------------------------------
@api_bp.route("/sessions/<session_id>/results")
def get_results(session_id: str):
    try:
        session = ReviewSession.load(session_id)
    except FileNotFoundError:
        return jsonify({"error": "会话不存在"}), 404

    return jsonify({
        "session_id": session_id,
        "status": session.status,
        "pdf_filename": session.pdf_filename,
        "agent_config": session.agent_config,
        "reviews": session.reviews,
        "editor_summary": session.editor_summary,
        "author_discussions": session.author_discussions,
        "final_markdown": session.final_markdown,
        "created_at": session.created_at,
    })


# ---------------------------------------------------------------------------
# Download final Markdown
# ---------------------------------------------------------------------------
@api_bp.route("/sessions/<session_id>/download")
def download_result(session_id: str):
    try:
        session = ReviewSession.load(session_id)
    except FileNotFoundError:
        return jsonify({"error": "会话不存在"}), 404

    if not session.final_markdown:
        return jsonify({"error": "修改报告尚未生成"}), 400

    import io
    md_bytes = session.final_markdown.encode("utf-8")
    return send_file(
        io.BytesIO(md_bytes),
        mimetype="text/markdown",
        as_attachment=True,
        download_name=f"revision_report_{session_id[:8]}.md",
    )


# ---------------------------------------------------------------------------
# Get available models
# ---------------------------------------------------------------------------
@api_bp.route("/models")
def get_models():
    return jsonify({
        "models": AVAILABLE_MODELS,
        "roles": AGENT_ROLES,
        "defaults": DEFAULT_MODELS,
    })


# ---------------------------------------------------------------------------
# Get supported venues
# ---------------------------------------------------------------------------
@api_bp.route("/venues")
def get_venues():
    return jsonify({
        "venues": [
            {"id": k, "name": v["name"], "type": v["type"]}
            for k, v in VENUES.items()
        ]
    })


# ---------------------------------------------------------------------------
# Background workflow runner
# ---------------------------------------------------------------------------
def _run_workflow(session_id: str, initial_state: dict, q: queue.Queue):
    try:
        graph = build_review_graph()
        session = ReviewSession.load(session_id)

        for chunk in graph.stream(initial_state, stream_mode="updates"):
            # chunk: {node_name: state_update_dict}
            for node_name, update in chunk.items():
                # Persist incremental results
                _apply_update_to_session(session, node_name, update)
                session.save()

                # Push progress events to SSE queue
                for event in update.get("progress_events", []):
                    q.put(event)

        # Mark complete
        session.status = "complete"
        session.save()

    except Exception as e:
        try:
            session = ReviewSession.load(session_id)
            session.status = "error"
            session.error = str(e)
            session.save()
        except Exception:
            pass
        q.put({
            "type": "error",
            "agent": "system",
            "phase": "error",
            "content": f"工作流执行出错：{str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
        })
    finally:
        q.put(None)  # sentinel


def _apply_update_to_session(session: ReviewSession, node_name: str, update: dict):
    """Merge a LangGraph state update into the persistent session object."""
    if "reviews" in update:
        session.reviews.extend(update["reviews"])
        session.status = "reviewing"
    if "editor_summary" in update and update["editor_summary"]:
        session.editor_summary = update["editor_summary"]
        session.status = "editing"
    if "author_discussions" in update:
        session.author_discussions.extend(update["author_discussions"])
        session.status = "discussing"
    if "final_revision_markdown" in update and update["final_revision_markdown"]:
        session.final_markdown = update["final_revision_markdown"]
