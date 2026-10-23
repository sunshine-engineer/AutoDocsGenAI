# File: examples/langchain_1_4_6_offline.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Author-written smoke example for langchain==1.4.6; no provider or API key.

This tests API wiring with fixed responses, not LLM quality or tool execution.
Run in the isolated exact-version environment described in docs/interview-demo.md.
"""

from importlib.metadata import version

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver


class ObserveModel(AgentMiddleware):
    """Middleware recording the order of before/after model hooks in an offline example."""

    def __init__(self):
        """Initialize observe model state for subsequent calls."""
        self.events: list[str] = []

    def before_model(self, state, runtime):
        """Record the before-model hook without modifying agent state.

        Args:
            state: Typed pipeline or agent state consumed by this operation.
            runtime: LangChain runtime context passed to the middleware hook.
        """
        self.events.append("before_model")

    def after_model(self, state, runtime):
        """Record the after-model hook without modifying agent state.

        Args:
            state: Typed pipeline or agent state consumed by this operation.
            runtime: LangChain runtime context passed to the middleware hook.
        """
        self.events.append("after_model")


def main():
    """Execute the pinned offline agent, middleware and state demonstration."""
    assert version("langchain") == "1.4.6", "Use the exact pilot release"
    middleware = ObserveModel()
    graph = create_agent(
        model=FakeMessagesListChatModel(
            responses=[
                AIMessage(content="First fixture reply"),
                AIMessage(content="Second fixture reply"),
            ]
        ),
        tools=[],
        system_prompt="Answer briefly.",
        middleware=[middleware],
        checkpointer=InMemorySaver(),
    )
    config: RunnableConfig = {"configurable": {"thread_id": "offline-demo"}}
    first = graph.invoke(
        {"messages": [{"role": "user", "content": "First fixture message"}]},
        config=config,
    )
    second = graph.invoke(
        {"messages": [{"role": "user", "content": "Second fixture message"}]},
        config=config,
    )
    assert len(first["messages"]) == 2
    assert len(second["messages"]) == 4
    assert second["messages"][-1].content == "Second fixture reply"
    assert middleware.events == ["before_model", "after_model"] * 2
    print(
        "PASS: exact release, agent invocation, middleware hooks, in-memory thread state"
    )
    print(
        "Fixture model only; no tool calling, real-provider quality, or disk persistence tested"
    )


if __name__ == "__main__":
    main()
