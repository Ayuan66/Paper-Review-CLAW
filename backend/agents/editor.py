from datetime import datetime
from llm.openrouter_client import OpenRouterClient
from agents.prompts import (
    EDITOR_SYSTEM_PROMPT,
    EDITOR_USER_PROMPT_TEMPLATE,
    EDITOR_SECOND_ROUND_SYSTEM_PROMPT,
    EDITOR_SECOND_ROUND_USER_TEMPLATE,
)
from graph.state import ReviewState

_client = OpenRouterClient()


def editor_node(state: ReviewState) -> dict:
    model = state["agent_config"].get("editor", "moonshotai/kimi-k2")
    review_round = state.get("review_round", 1)

    round_label = "第二轮" if review_round == 2 else "第一轮"
    start_event = {
        "type": "start",
        "agent": "editor",
        "phase": "editing",
        "content": f"编辑开始汇总{round_label}审稿意见...",
        "timestamp": datetime.utcnow().isoformat(),
    }

    if review_round == 2:
        # Round 2: use reviews_round2 and include author response
        reviews_map = {r["agent_name"]: r["content"] for r in state.get("reviews_round2", [])}
        review_1 = reviews_map.get("reviewer_1", "（无）")
        review_2 = reviews_map.get("reviewer_2", "（无）")
        review_3 = reviews_map.get("reviewer_3", "（无）")
        author_response = (
            state.get("author_response_edited")
            or state.get("author_response", "（无）")
        )
        user_prompt = EDITOR_SECOND_ROUND_USER_TEMPLATE.format(
            author_response=author_response,
            review_1=review_1,
            review_2=review_2,
            review_3=review_3,
        )
        system_prompt = EDITOR_SECOND_ROUND_SYSTEM_PROMPT
    else:
        # Round 1: standard editor flow
        reviews_map = {r["agent_name"]: r["content"] for r in state["reviews"]}
        review_1 = reviews_map.get("reviewer_1", "（无）")
        review_2 = reviews_map.get("reviewer_2", "（无）")
        review_3 = reviews_map.get("reviewer_3", "（无）")
        user_prompt = EDITOR_USER_PROMPT_TEMPLATE.format(
            review_1=review_1,
            review_2=review_2,
            review_3=review_3,
        )
        system_prompt = EDITOR_SYSTEM_PROMPT

    try:
        content = _client.chat_text(
            model=model,
            system_prompt=system_prompt,
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
        if review_round == 2:
            return {
                "editor_summary_round2": content,
                "progress_events": [start_event, done_event],
            }
        return {
            "editor_summary": content,
            "current_phase": "author_responding",
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
        if review_round == 2:
            return {
                "editor_summary_round2": error_content,
                "progress_events": [start_event, error_event],
            }
        return {
            "editor_summary": error_content,
            "current_phase": "author_responding",
            "progress_events": [start_event, error_event],
        }

