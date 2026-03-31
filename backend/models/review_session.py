import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from config import SESSIONS_DIR


@dataclass
class ReviewSession:
    session_id: str
    pdf_filename: str
    pdf_path: str
    agent_config: dict = field(default_factory=dict)
    status: str = "created"
    # created | reviewing | editing | author_responding | waiting_for_author_edit
    # | complete | error
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Phase 1 results
    venue: str = ""
    venue_context: str = ""
    reviews: list = field(default_factory=list)
    editor_summary: str = ""
    author_response: str = ""          # AI-generated author response
    author_response_edited: str = ""   # User-edited version (used for phase 2)

    # Phase 2 results
    reviews_round2: list = field(default_factory=list)
    editor_summary_round2: str = ""

    # Final output
    final_markdown: str = ""
    error: str = ""

    # Kept for backward compatibility with old session JSON files
    author_discussions: list = field(default_factory=list)

    def save(self):
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        path = os.path.join(SESSIONS_DIR, f"{self.session_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, session_id: str) -> "ReviewSession":
        path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Session {session_id} not found")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Filter out unknown keys for forward/backward compatibility
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    def to_dict(self) -> dict:
        return asdict(self)

