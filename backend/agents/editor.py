from datetime import datetime
from llm.openrouter_client import OpenRouterClient
from agents.prompts import EDITOR_SYSTEM_PROMPT, EDITOR_USER_PROMPT_TEMPLATE
from graph.state import ReviewState

_client = OpenRouterClient()


def editor_node(state: ReviewState) -> dict:
    model = state["agent_config"].get("editor", "moonshotai/kimi-k2")

    start_event = {
        "type": "start",
        "agent": "editor",
        "phase": "editing",
        "content": "编辑开始汇总审稿意见...",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Map reviews by agent_name
    reviews_map = {r["agent_name"]: r["content"] for r in state["reviews"]}
    review_1 = reviews_map.get("reviewer_1", "（无）")
    review_2 = reviews_map.get("reviewer_2", "（无）")
    review_3 = reviews_map.get("reviewer_3", "（无）")

    user_prompt = EDITOR_USER_PROMPT_TEMPLATE.format(
        review_1=review_1,
        review_2=review_2,
        review_3=review_3,
    )

    try:
        content = _client.chat_text(
            model=model,
            system_prompt=EDITOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=4096,
        )
        done_event = {
            "type": "complete",
            "agent": "editor",
            "phase": "editing",
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return {
            "editor_summary": content,
            "current_phase": "discussing",
            "progress_events": [start_event, done_event],
        }
    except Exception as e:
        error_content = f"[编辑汇总失败] {str(e)}"
        error_event = {
            "type": "error",
            "agent": "editor",
            "phase": "editing",
            "content": error_content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return {
            "editor_summary": error_content,
            "current_phase": "discussing",
            "progress_events": [start_event, error_event],
        }
