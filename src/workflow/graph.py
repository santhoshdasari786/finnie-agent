from langgraph.graph import END, START, StateGraph
from src.workflow.nodes import make_nodes
from src.workflow.state import GraphState


def _after_guard(state: GraphState) -> str:
    return "respond_blocked" if state["guard"].blocked else "contextualize"


def build_graph(agents, guardrails, settings, memory=None, classifier=None, classifier_timeout: float = 8.0):
    nodes = make_nodes(agents,guardrails, settings,memory, classifier, classifier_timeout)
    g = StateGraph(GraphState)
    for name, fn in nodes.items():
        g.add_node(name, fn)

    g.add_edge(START, "input_guard")
    g.add_conditional_edges("input_guard", _after_guard, ["respond_blocked", "contextualize"])
    g.add_edge("contextualize","route")
    g.add_edge("route", "run_agent")
    g.add_edge("run_agent","output_guard")
    g.add_edge("output_guard", "remember")
    g.add_edge("remember", END)
    g.add_edge("respond_blocked", END)
    return g.compile()

async def ask(app, text, thread_id="default", agent=None):
    out = await app.ainvoke({"text":text, "thread_id":thread_id, "agent":agent})
    return out["result"]

    