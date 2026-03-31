from datetime import datetime
from llm.openrouter_client import OpenRouterClient
from agents.prompts import (
    build_reviewer_system_prompt,
    REVIEWER_USER_PROMPT,
    REVIEWER_SECOND_ROUND_USER_PROMPT_PREFIX,
)
from graph.state import ReviewState

_client = OpenRouterClient()


def make_reviewer_node(agent_key: str):
    """Factory: returns a LangGraph node function for the given reviewer key."""

    def reviewer_node(state: ReviewState) -> dict:
        model = state["agent_config"].get(agent_key, "openai/gpt-4o")
        page_images = state.get("pdf_page_images", [])
        review_round = state.get("review_round", 1)

        round_label = f"第{review_round}轮" if review_round > 1 else "第1轮"
        start_event = {
            "type": "start",
            "agent": agent_key,
            "phase": "reviewing",
            "content": f"审稿人开始{round_label}审阅论文《{state['pdf_filename']}》（共{len(page_images)}页）",
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            system_prompt = build_reviewer_system_prompt(
                venue=state.get("venue", ""),
                venue_context=state.get("venue_context", ""),
            )

            if review_round == 2:
                # Round 2: include author response as context
                author_response = (
                    state.get("author_response_edited")
                    or state.get("author_response", "")
                )
                user_prompt = REVIEWER_SECOND_ROUND_USER_PROMPT_PREFIX.format(
                    author_response=author_response
                )
            else:
                user_prompt = REVIEWER_USER_PROMPT

            content = _client.chat_with_paper(
                model=model,
                pdf_text=state["pdf_text"],
                pdf_filename=state["pdf_filename"],
                page_images=page_images,
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=4096,
            )
            review_entry = {"agent_name": agent_key, "model": model, "content": content}
            done_event = {
                "type": "complete",
                "agent": agent_key,
                "phase": "reviewing",
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Round 2 results go to reviews_round2; round 1 to reviews
            if review_round == 2:
                return {
                    "reviews_round2": [review_entry],
                    "progress_events": [start_event, done_event],
                }
            return {
                "reviews": [review_entry],
                "progress_events": [start_event, done_event],
            }
        except Exception as e:
            error_content = f"[审稿失败] {str(e)}"
            review_entry = {"agent_name": agent_key, "model": model, "content": error_content}
            error_event = {
                "type": "error",
                "agent": agent_key,
                "phase": "reviewing",
                "content": error_content,
                "timestamp": datetime.utcnow().isoformat(),
            }
            if review_round == 2:
                return {
                    "reviews_round2": [review_entry],
                    "progress_events": [start_event, error_event],
                }
            return {
                "reviews": [review_entry],
                "progress_events": [start_event, error_event],
            }

    reviewer_node.__name__ = agent_key
    return reviewer_node

