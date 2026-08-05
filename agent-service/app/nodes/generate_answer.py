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


def generate_answer_node(state: FinanceAgentState) -> FinanceAgentState:
    model = _get_chat_model()

    memory_context = state.get("memory_context") or "No confirmed user preferences."

    system_prompt = f"""
You are a finance AI assistant.

Use confirmed user preferences only for response style, tone, workflow, and formatting.
Do not treat user memory as factual financial evidence.
Do not invent financial facts.
Avoid personalized investment advice.
If the user asks for investment advice, keep the answer educational and cautious.

Confirmed user preferences:
{memory_context}
""".strip()

    user_prompt = f"""
User question:
{state["question"]}

Answer using the confirmed preferences when helpful.
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