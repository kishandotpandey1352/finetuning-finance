import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.graphs.state import FinanceAgentState


def _get_chat_model() -> ChatOpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for agent answer generation.")

    return ChatOpenAI(
        model=settings.agent_model,
        temperature=0.2,
        api_key=settings.openai_api_key,
    )


def _format_tool_results(state: FinanceAgentState) -> str:
    tool_results = state.get("tool_results", [])

    if not tool_results:
        return "No tool results."

    return json.dumps(
        [result.model_dump(mode="json") for result in tool_results],
        indent=2,
    )


def generate_answer_node(state: FinanceAgentState) -> FinanceAgentState:
    model = _get_chat_model()

    memory_context = state.get("memory_context") or "No confirmed user preferences."
    tool_results = _format_tool_results(state)
    tool_plan = state.get("tool_plan")

    system_prompt = f"""
You are a finance AI assistant.

Use confirmed user preferences only for response style, tone, workflow, and formatting.
Do not treat user memory as factual financial evidence.
Use deterministic tool results when they are available.
Do not invent financial facts.
Avoid personalized investment advice.
If the user asks for investment advice, keep the answer educational and cautious.

Confirmed user preferences:
{memory_context}

Tool plan:
{tool_plan.model_dump(mode="json") if tool_plan else "No tool plan."}

Tool results:
{tool_results}
""".strip()

    user_prompt = f"""
User question:
{state["question"]}

Answer clearly. If a calculator result exists, use it instead of doing mental arithmetic.
""".strip()

    response = model.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )

    content = response.content

    if not isinstance(content, str):
        content = str(content)

    return {
        **state,
        "answer": content,
        "model": settings.agent_model,
    }