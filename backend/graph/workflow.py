from datetime import datetime

from langgraph.graph import StateGraph, START, END

from graph.state import ReviewState
from agents.reviewer import make_reviewer_node
from agents.editor import editor_node
from agents.author import author_node, finalize_node
from llm.openrouter_client import OpenRouterClient
from llm.venue_fetcher import get_venue_context

_client = OpenRouterClient()


def prepare_node(state: ReviewState) -> dict:
    """Fetch venue review criteria before reviewers start."""
    venue = state.get("venue", "")
    if not venue:
        return {
            "venue_context": "",
            "progress_events": [],
        }

    start_event = {
        "type": "start",
        "agent": "prepare",
        "phase": "preparing",
        "preview": f"正在从官网获取 {venue} 的审稿标准...",
        "timestamp": datetime.utcnow().isoformat(),
    }
    try:
        context = get_venue_context(venue, _client)
        done_event = {
            "type": "complete",
            "agent": "prepare",
            "phase": "preparing",
            "preview": f"已获取 {venue} 审稿标准（{len(context)} 字）",
            "timestamp": datetime.utcnow().isoformat(),
        }
        return {
            "venue_context": context,
            "progress_events": [start_event, done_event],
        }
    except Exception as e:
        error_event = {
            "type": "error",
            "agent": "prepare",
            "phase": "preparing",
            "preview": f"获取 {venue} 信息失败：{e}",
            "timestamp": datetime.utcnow().isoformat(),
        }
        return {
            "venue_context": "",
            "progress_events": [start_event, error_event],
        }


def build_phase1_graph():
    """Phase 1: prepare → 3 reviewers (parallel) → editor → author → END"""
    graph = StateGraph(ReviewState)

    graph.add_node("prepare", prepare_node)
    graph.add_node("reviewer_1", make_reviewer_node("reviewer_1"))
    graph.add_node("reviewer_2", make_reviewer_node("reviewer_2"))
    graph.add_node("reviewer_3", make_reviewer_node("reviewer_3"))
    graph.add_node("editor", editor_node)
    graph.add_node("author", author_node)

    graph.add_edge(START, "prepare")

    # prepare → fan-out to 3 reviewers in parallel
    graph.add_edge("prepare", "reviewer_1")
    graph.add_edge("prepare", "reviewer_2")
    graph.add_edge("prepare", "reviewer_3")

    # fan-in → editor → author → END
    graph.add_edge("reviewer_1", "editor")
    graph.add_edge("reviewer_2", "editor")
    graph.add_edge("reviewer_3", "editor")

    graph.add_edge("editor", "author")
    graph.add_edge("author", END)

    return graph.compile()


def build_phase2_graph():
    """Phase 2: 3 reviewers round2 (parallel) → editor round2 → finalize → END"""
    graph = StateGraph(ReviewState)

    graph.add_node("reviewer_1", make_reviewer_node("reviewer_1"))
    graph.add_node("reviewer_2", make_reviewer_node("reviewer_2"))
    graph.add_node("reviewer_3", make_reviewer_node("reviewer_3"))
    graph.add_node("editor", editor_node)
    graph.add_node("finalize", finalize_node)

    # All 3 reviewers start in parallel
    graph.add_edge(START, "reviewer_1")
    graph.add_edge(START, "reviewer_2")
    graph.add_edge(START, "reviewer_3")

    # fan-in → editor → finalize → END
    graph.add_edge("reviewer_1", "editor")
    graph.add_edge("reviewer_2", "editor")
    graph.add_edge("reviewer_3", "editor")

    graph.add_edge("editor", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()

