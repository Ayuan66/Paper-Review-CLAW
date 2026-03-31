import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from config import SESSIONS_DIR


@dataclass
class IdeaSession:
    session_id: str
    research_question: str
    agent_config: dict = field(default_factory=dict)
    status: str = "created"
    # created | discussing | waiting_for_input | waiting_for_revision | complete | error
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    user_context: str = ""          # Optional background / constraints from user
    current_round: int = 0
    max_rounds: int = 3

    # Discussion records: [{round, agent, role, content, timestamp}]
    discussions: list = field(default_factory=list)
    # Per-round summaries: [{round, content}]
    summaries: list = field(default_factory=list)
    # User answers to agent questions: [{round, agent, question, answer, timestamp}]
    user_answers: list = field(default_factory=list)
    # Semantic Scholar results: [{title, authors, year, citationCount, abstract, tldr, url}]
    search_results: list = field(default_factory=list)

    # Current pending question (when status == waiting_for_input)
    pending_question: str = ""
    pending_question_agent: str = ""

    error: str = ""

    def save(self):
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        path = os.path.join(SESSIONS_DIR, f"idea_{self.session_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, session_id: str) -> "IdeaSession":
        path = os.path.join(SESSIONS_DIR, f"idea_{session_id}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"IdeaSession {session_id} not found")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    def to_dict(self) -> dict:
        return asdict(self)
