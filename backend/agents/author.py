from datetime import datetime
from llm.openrouter_client import OpenRouterClient
from agents.prompts import (
    AUTHOR_A_SYSTEM_PROMPT,
    AUTHOR_A_FIRST_ROUND_TEMPLATE,
    AUTHOR_A_SUBSEQUENT_ROUND_TEMPLATE,
    AUTHOR_B_SYSTEM_PROMPT,
    AUTHOR_B_USER_TEMPLATE,
    FINALIZE_SYSTEM_PROMPT,
    FINALIZE_USER_TEMPLATE,
)
from graph.state import ReviewState

_client = OpenRouterClient()

CONSENSUS_MARKER = "[共识已达成]"


def author_a_node(state: ReviewState) -> dict:
    model = state["agent_config"].get("author_a", "openai/gpt-4o")
    iteration = state.get("author_iteration", 0)

    start_event = {
        "type": "start",
        "agent": "author_a",
        "phase": "discussing",
        "content": f"作者A开始第 {iteration + 1} 轮修改讨论...",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Build user prompt based on whether this is first or subsequent round
    discussions = state.get("author_discussions", [])
    author_b_messages = [d for d in discussions if d["author"] == "author_b"]

    if not author_b_messages:
        # First round
        user_prompt = AUTHOR_A_FIRST_ROUND_TEMPLATE.format(
            editor_summary=state["editor_summary"]
        )
    else:
        # Subsequent rounds: use Author B's last message
        last_b_message = author_b_messages[-1]["content"]
        user_prompt = AUTHOR_A_SUBSEQUENT_ROUND_TEMPLATE.format(
            author_b_last_message=last_b_message
        )

    try:
        content = _client.chat_text(
            model=model,
            system_prompt=AUTHOR_A_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=4096,
        )
        discussion_entry = {
            "round": iteration + 1,
            "author": "author_a",
            "model": model,
            "content": content,
        }
        done_event = {
            "type": "complete",
            "agent": "author_a",
            "phase": "discussing",
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return {
            "author_discussions": [discussion_entry],
            "author_iteration": iteration + 1,
            "progress_events": [start_event, done_event],
        }
    except Exception as e:
        error_content = f"[作者A响应失败] {str(e)}"
        discussion_entry = {
            "round": iteration + 1,
            "author": "author_a",
            "model": model,
            "content": error_content,
        }
        error_event = {
            "type": "error",
            "agent": "author_a",
            "phase": "discussing",
            "content": error_content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return {
            "author_discussions": [discussion_entry],
            "author_iteration": iteration + 1,
            "progress_events": [start_event, error_event],
        }


def author_b_node(state: ReviewState) -> dict:
    model = state["agent_config"].get("author_b", "deepseek/deepseek-chat")
    iteration = state.get("author_iteration", 1)

    start_event = {
        "type": "start",
        "agent": "author_b",
        "phase": "discussing",
        "content": f"作者B开始审阅第 {iteration} 轮修改方案...",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Get Author A's last message
    discussions = state.get("author_discussions", [])
    author_a_messages = [d for d in discussions if d["author"] == "author_a"]
    last_a_message = author_a_messages[-1]["content"] if author_a_messages else ""

    user_prompt = AUTHOR_B_USER_TEMPLATE.format(
        editor_summary=state["editor_summary"],
        author_a_last_message=last_a_message,
    )

    try:
        content = _client.chat_text(
            model=model,
            system_prompt=AUTHOR_B_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=4096,
        )
        reached_consensus = CONSENSUS_MARKER in content
        discussion_entry = {
            "round": iteration,
            "author": "author_b",
            "model": model,
            "content": content,
        }
        done_event = {
            "type": "complete",
            "agent": "author_b",
            "phase": "discussing",
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return {
            "author_discussions": [discussion_entry],
            "authors_reached_consensus": reached_consensus,
            "progress_events": [start_event, done_event],
        }
    except Exception as e:
        error_content = f"[作者B响应失败] {str(e)}"
        discussion_entry = {
            "round": iteration,
            "author": "author_b",
            "model": model,
            "content": error_content,
        }
        error_event = {
            "type": "error",
            "agent": "author_b",
            "phase": "discussing",
            "content": error_content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return {
            "author_discussions": [discussion_entry],
            "authors_reached_consensus": False,
            "progress_events": [start_event, error_event],
        }


def finalize_node(state: ReviewState) -> dict:
    model = state["agent_config"].get("author_a", "openai/gpt-4o")

    start_event = {
        "type": "start",
        "agent": "finalize",
        "phase": "finalizing",
        "content": "正在生成最终修改报告...",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Format author discussions for the prompt
    discussions_text = ""
    for d in state.get("author_discussions", []):
        role_label = "作者A" if d["author"] == "author_a" else "作者B"
        discussions_text += f"\n\n**第{d['round']}轮 - {role_label}：**\n{d['content']}"

    user_prompt = FINALIZE_USER_TEMPLATE.format(
        editor_summary=state["editor_summary"],
        author_discussions=discussions_text.strip(),
    )

    try:
        content = _client.chat_text(
            model=model,
            system_prompt=FINALIZE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=6000,
        )
        done_event = {
            "type": "complete",
            "agent": "finalize",
            "phase": "complete",
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
            "phase": "complete",
            "content": error_content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return {
            "final_revision_markdown": error_content,
            "current_phase": "complete",
            "progress_events": [start_event, error_event],
        }
