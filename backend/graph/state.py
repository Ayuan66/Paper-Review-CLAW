import operator
from typing import Annotated, TypedDict


class ReviewState(TypedDict):
    # Input
    session_id: str
    pdf_base64: str
    pdf_filename: str
    pdf_text: str              # Extracted plain text from PDF
    pdf_page_images: list[str] # Base64 PNG per page (for vision models)
    agent_config: dict         # {"reviewer_1": "openai/gpt-4o", ...}
    venue: str                 # e.g. "ICSE", "TSE", or "" for generic
    venue_context: str         # Fetched+summarized venue review criteria (Chinese)

    # Which review round: 1 = Phase 1 (first review), 2 = Phase 2 (second review)
    review_round: int

    # Phase 1 — Round 1 reviews (parallel fan-in)
    reviews: Annotated[list[dict], operator.add]
    # Each dict: {"agent_name": str, "model": str, "content": str}

    # Phase 1 — Editor summary (round 1)
    editor_summary: str

    # Phase 1 — Single author response (no discussion loop)
    author_response: str         # AI-generated author response to editor summary
    author_response_edited: str  # User-edited version, passed into phase 2

    # Phase 2 — Round 2 reviews (parallel fan-in)
    reviews_round2: Annotated[list[dict], operator.add]

    # Phase 2 — Editor summary (round 2)
    editor_summary_round2: str

    # Final output
    final_revision_markdown: str

    # Progress streaming
    current_phase: str  # "reviewing" | "editing" | "author_responding" | "finalizing" | "complete" | "error"
    progress_events: Annotated[list[dict], operator.add]
    # Each event: {"type": str, "agent": str, "phase": str, "content": str, "timestamp": str}
