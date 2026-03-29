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

    # Phase 1: Reviews (list reducer for parallel fan-in)
    reviews: Annotated[list[dict], operator.add]
    # Each dict: {"agent_name": str, "model": str, "content": str}

    # Phase 2: Editor summary
    editor_summary: str

    # Phase 3: Author discussion
    author_discussions: Annotated[list[dict], operator.add]
    # Each dict: {"round": int, "author": str, "model": str, "content": str}
    author_iteration: int
    max_author_iterations: int
    authors_reached_consensus: bool

    # Final output
    final_revision_markdown: str

    # Progress streaming
    current_phase: str  # "reviewing" | "editing" | "discussing" | "complete" | "error"
    progress_events: Annotated[list[dict], operator.add]
    # Each event: {"type": str, "agent": str, "phase": str, "content": str, "timestamp": str}
