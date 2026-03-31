from datetime import datetime
from llm.openrouter_client import OpenRouterClient
from agents.prompts import (
    AUTHOR_SYSTEM_PROMPT,
    AUTHOR_USER_TEMPLATE,
    FINALIZE_SYSTEM_PROMPT,
    FINALIZE_USER_TEMPLATE,
)
from graph.state import ReviewState

_client = OpenRouterClient()


def author_node(state: ReviewState) -> dict:
    model = state["agent_config"].get("author", "openai/gpt-4o")

    start_event = {
        "type": "start",
        "agent": "author",
        "phase": "author_responding",
        "content": "作者开始撰写修改方案...",
        "timestamp": datetime.utcnow().isoformat(),
    }

    user_prompt = AUTHOR_USER_TEMPLATE.format(
        editor_summary=state["editor_summary"]
    )

    try:
        content = _client.chat_text(
            model=model,
            system_prompt=AUTHOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=4096,
        )
        done_event = {
            "type": "complete",
            "agent": "author",
            "phase": "author_responding",
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return {
            "author_response": content,
            "progress_events": [start_event, done_event],
        }
    except Exception as e:
        error_content = f"[作者响应失败] {str(e)}"
        error_event = {
            "type": "error",
            "agent": "author",
            "phase": "author_responding",
            "content": error_content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return {
            "author_response": error_content,
            "progress_events": [start_event, error_event],
        }


def finalize_node(state: ReviewState) -> dict:
    model = state["agent_config"].get("editor", "deepseek/deepseek-chat")

    start_event = {
        "type": "start",
        "agent": "finalize",
        "phase": "finalizing",
        "content": "正在生成最终修改报告...",
        "timestamp": datetime.utcnow().isoformat(),
    }

    author_response = state.get("author_response_edited") or state.get("author_response", "（无）")
    editor_summary = state.get("editor_summary", "（无）")
    editor_summary_round2 = state.get("editor_summary_round2", "（无）")

    user_prompt = FINALIZE_USER_TEMPLATE.format(
        editor_summary=editor_summary,
        author_response=author_response,
        editor_summary_round2=editor_summary_round2,
    )

    try:
        content = _client.chat_text(
            model=model,
            system_prompt=FINALIZE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=8192,
        )
        done_event = {
            "type": "complete",
            "agent": "finalize",
            "phase": "finalizing",
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return {
            "final_revision_markdown": content,
            "current_phase": "complete",
            "progress_events": [start_event, done_event],
        }
    except Exception as e:
        error_content = f"[报告生成失败] {str(e)}"
        error_event = {
            "type": "error",
            "agent": "finalize",
            "phase": "finalizing",
            "content": error_content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return {
            "final_revision_markdown": error_content,
            "current_phase": "error",
            "progress_events": [start_event, error_event],
        }
