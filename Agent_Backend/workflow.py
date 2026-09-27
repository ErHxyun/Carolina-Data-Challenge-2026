"""Request-scoped LangGraph workflows; existing HTTP/NDJSON contracts stay stable."""
from typing import TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import START, END, StateGraph


class RouteState(TypedDict, total=False):
    question: str
    current_country: str | None
    route: dict


class ReportState(TypedDict, total=False):
    route: dict
    bundle: dict
    statistics: dict
    research: dict
    report: dict


def create_route_graph(resolve):
    def locate(state):
        return {"route": resolve(state["question"], state.get("current_country"))}

    graph = StateGraph(RouteState)
    graph.add_node("router", locate)
    graph.add_edge(START, "router")
    graph.add_edge("router", END)
    return graph.compile()


def create_report_graph(validate, load_data, statistics, research, write_report, write_roadmap=None):
    def prepare(state):
        route = validate(state["route"])
        return {"route": route, "bundle": load_data(route)}

    def analyze(state):
        emit = get_stream_writer()
        emit({"stage": "statistics", "status": "running"})
        result = statistics(state["bundle"])
        emit({"stage": "statistics", "status": "complete" if result["status"] == "complete" else "limited"})
        return {"statistics": result}

    def search(state):
        emit = get_stream_writer()
        emit({"stage": "research", "status": "running"})
        result = research(state["route"], state["bundle"])
        emit({"stage": "research", "status": "complete" if result["status"] == "complete" else "limited"})
        return {"research": result}

    def report(state):
        emit = get_stream_writer()
        emit({"stage": "report", "status": "running"})
        result = write_report(state["route"], state["bundle"], state["statistics"], state["research"])
        emit({"stage": "report", "status": "complete" if result["status"] == "complete" else "limited"})
        return {"report": result}

    def roadmap(state):
        emit = get_stream_writer()
        emit({"stage": "roadmap", "status": "running"})
        result = write_roadmap(state["route"], state["bundle"], state["statistics"], state["research"])
        emit({"stage": "roadmap", "status": "complete" if result["status"] == "complete" else "limited"})
        return {"report": result}

    graph = StateGraph(ReportState)
    graph.add_node("prepare", prepare)
    graph.add_node("statistics", analyze)
    graph.add_node("research", search)
    graph.add_node("report", report)
    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "statistics")
    graph.add_edge("prepare", "research")
    # A single join waits for BOTH branches and runs report exactly once.
    graph.add_node("choose_output", lambda state: {})
    graph.add_edge(["statistics", "research"], "choose_output")
    graph.add_node("roadmap", roadmap)
    graph.add_conditional_edges("choose_output", lambda state: "roadmap" if write_roadmap and state["route"].get("output_mode") == "policy_roadmap" else "report", {"roadmap": "roadmap", "report": "report"})
    graph.add_edge("roadmap", END)
    graph.add_edge("report", END)
    return graph.compile()


def run_report_graph(graph, route, progress):
    result = None
    # Consume node events on one thread: parallel nodes never write HTTP bytes.
    for mode, payload in graph.stream({"route": route}, stream_mode=["custom", "updates"]):
        if mode == "custom":
            progress(payload["stage"], payload["status"])
        else:
            for update in payload.values():
                if isinstance(update, dict) and "report" in update:
                    result = update["report"]
    if result is None:
        raise RuntimeError("Report workflow finished without a report")
    return result
