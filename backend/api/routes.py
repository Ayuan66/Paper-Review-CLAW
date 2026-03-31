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
    UPLOADS_DIR,
    VENUES,
)
from graph.workflow import build_phase1_graph, build_phase2_graph
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
# Start review process (Phase 1)
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
    venue = body.get("venue", "")  # e.g. "ICSE", "TSE", or ""

    session.agent_config = agent_config
    session.venue = venue
    session.status = "reviewing"
    # Reset any previous results when restarting
    session.reviews = []
    session.editor_summary = ""
    session.author_response = ""
    session.author_response_edited = ""
    session.reviews_round2 = []
    session.editor_summary_round2 = ""
    session.final_markdown = ""
    session.error = ""
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
        "review_round": 1,
        "reviews": [],
        "editor_summary": "",
        "author_response": "",
        "author_response_edited": "",
        "reviews_round2": [],
        "editor_summary_round2": "",
        "final_revision_markdown": "",
        "current_phase": "reviewing",
        "progress_events": [],
    }

    q: queue.Queue = queue.Queue()
    _session_queues[session_id] = q

    thread = threading.Thread(
        target=_run_workflow,
        args=(session_id, initial_state, q, 1),
        daemon=True,
    )
    thread.start()

    return jsonify({"status": "started"})


# ---------------------------------------------------------------------------
# Submit user-edited author response and start Phase 2
# ---------------------------------------------------------------------------
@api_bp.route("/sessions/<session_id>/submit-author-response", methods=["POST"])
def submit_author_response(session_id: str):
    try:
        session = ReviewSession.load(session_id)
    except FileNotFoundError:
        return jsonify({"error": "会话不存在"}), 404

    if session.status != "waiting_for_author_edit":
        return jsonify({"error": f"当前状态 {session.status} 不允许提交修改意见"}), 400

    body = request.get_json(silent=True) or {}
    edited_response = body.get("author_response", "").strip()
    if not edited_response:
        return jsonify({"error": "修改意见不能为空"}), 400

    session.author_response_edited = edited_response
    session.status = "reviewing"
    session.reviews_round2 = []
    session.editor_summary_round2 = ""
    session.final_markdown = ""
    session.save()

    # Re-read and re-extract PDF
    with open(session.pdf_path, "rb") as f:
        pdf_bytes = f.read()
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    _pdf_bytes, pdf_text, page_images = extract_from_base64(pdf_base64)

    phase2_state = {
        "session_id": session_id,
        "pdf_base64": pdf_base64,
        "pdf_filename": session.pdf_filename,
        "pdf_text": pdf_text,
        "pdf_page_images": page_images,
        "agent_config": session.agent_config,
        "venue": session.venue,
        "venue_context": session.venue_context,
        "review_round": 2,
        "reviews": session.reviews,
        "editor_summary": session.editor_summary,
        "author_response": session.author_response,
        "author_response_edited": edited_response,
        "reviews_round2": [],
        "editor_summary_round2": "",
        "final_revision_markdown": "",
        "current_phase": "reviewing",
        "progress_events": [],
    }

    q: queue.Queue = queue.Queue()
    _session_queues[session_id] = q

    thread = threading.Thread(
        target=_run_workflow,
        args=(session_id, phase2_state, q, 2),
        daemon=True,
    )
    thread.start()

    return jsonify({"status": "phase2_started"})


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
        "author_response": session.author_response,
        "author_response_edited": session.author_response_edited,
        "reviews_round2": session.reviews_round2,
        "editor_summary_round2": session.editor_summary_round2,
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
# Download ZIP package (all review outputs + original PDF)
# ---------------------------------------------------------------------------
@api_bp.route("/sessions/<session_id>/download/zip")
def download_zip(session_id: str):
    import io
    import zipfile

    try:
        session = ReviewSession.load(session_id)
    except FileNotFoundError:
        return jsonify({"error": "会话不存在"}), 404

    if session.status != "complete":
        return jsonify({"error": "评审尚未完成，无法下载"}), 400

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Original PDF
        if os.path.exists(session.pdf_path):
            with open(session.pdf_path, "rb") as f:
                zf.writestr(session.pdf_filename, f.read())

        # Individual reviewer reports
        for review in session.reviews or []:
            agent = review.get("agent_name", "reviewer")
            model = review.get("model", "")
            content = review.get("content", "")
            md = f"# {agent} Review\n\n**Model**: `{model}`\n\n---\n\n{content}"
            zf.writestr(f"{agent}_review.md", md.encode("utf-8"))

        # Editor summary
        if session.editor_summary:
            md = f"# Editor Summary (Round 1)\n\n{session.editor_summary}"
            zf.writestr("editor_summary_round1.md", md.encode("utf-8"))

        # Author response
        if session.author_response_edited or session.author_response:
            response_text = session.author_response_edited or session.author_response
            edited_note = " (User Edited)" if session.author_response_edited else " (AI Generated)"
            md = f"# Author Response{edited_note}\n\n{response_text}"
            zf.writestr("author_response.md", md.encode("utf-8"))

        # Editor summary round 2
        if session.editor_summary_round2:
            md = f"# Editor Summary (Round 2)\n\n{session.editor_summary_round2}"
            zf.writestr("editor_summary_round2.md", md.encode("utf-8"))

        # Author discussions (legacy - round 2 reviews)
        if session.reviews_round2:
            lines = ["# Round 2 Reviews\n"]
            for r in session.reviews_round2:
                agent = r.get("agent_name", "reviewer")
                model = r.get("model", "")
                content = r.get("content", "")
                lines.append(f"## {agent} (Round 2)\n\n**Model**: `{model}`\n\n---\n\n{content}\n")
            zf.writestr("reviews_round2.md", "\n".join(lines).encode("utf-8"))

        # Final revision report
        if session.final_markdown:
            zf.writestr("revision_report.md", session.final_markdown.encode("utf-8"))

        # Metadata JSON
        metadata = {
            "session_id": session.session_id,
            "pdf_filename": session.pdf_filename,
            "created_at": session.created_at,
            "agent_config": session.agent_config,
            "status": session.status,
        }
        zf.writestr(
            "review_metadata.json",
            json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"),
        )

    buf.seek(0)
    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"review_package_{session_id[:8]}.zip",
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
def _run_workflow(session_id: str, initial_state: dict, q: queue.Queue, phase: int = 1):
    try:
        graph = build_phase1_graph() if phase == 1 else build_phase2_graph()
        session = ReviewSession.load(session_id)

        for chunk in graph.stream(initial_state, stream_mode="updates"):
            # chunk: {node_name: state_update_dict}
            for node_name, update in chunk.items():
                # Persist incremental results
                _apply_update_to_session(session, node_name, update, phase)
                session.save()

                # Push progress events to SSE queue
                for event in update.get("progress_events", []):
                    q.put(event)

        # Phase 1 complete: wait for user to edit author response
        # Phase 2 complete: fully done
        if phase == 1:
            session.status = "waiting_for_author_edit"
        else:
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


def _apply_update_to_session(session: ReviewSession, node_name: str, update: dict, phase: int = 1):
    """Merge a LangGraph state update into the persistent session object."""
    if "venue_context" in update and update["venue_context"]:
        session.venue_context = update["venue_context"]
    if "reviews" in update:
        session.reviews.extend(update["reviews"])
        session.status = "reviewing"
    if "reviews_round2" in update:
        session.reviews_round2.extend(update["reviews_round2"])
        session.status = "reviewing"
    if "editor_summary" in update and update["editor_summary"]:
        session.editor_summary = update["editor_summary"]
        session.status = "editing"
    if "editor_summary_round2" in update and update["editor_summary_round2"]:
        session.editor_summary_round2 = update["editor_summary_round2"]
        session.status = "editing"
    if "author_response" in update and update["author_response"]:
        session.author_response = update["author_response"]
        session.status = "author_responding"
    if "final_revision_markdown" in update and update["final_revision_markdown"]:
        session.final_markdown = update["final_revision_markdown"]
