from langgraph.graph import END, START, StateGraph

from app.graphs.state import FinanceAgentState
from app.nodes.generate_answer import generate_answer_node
from app.nodes.load_memory import load_memory_node


def build_finance_memory_graph():
    graph = StateGraph(FinanceAgentState)

    graph.add_node("load_memory", load_memory_node)
    graph.add_node("generate_answer", generate_answer_node)

    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "generate_answer")
    graph.add_edge("generate_answer", END)

    return graph.compile()