# File: examples/learning/langchain_1_4_6/02_middleware.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Observe synchronous model calls without changing the conversation state."""

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage


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


observer = ObserveModel()
agent = create_agent(
    model=FakeMessagesListChatModel(responses=[AIMessage(content="Observed reply")]),
    tools=[],
    middleware=[observer],
)
result = agent.invoke({"messages": [{"role": "user", "content": "Hello"}]})
assert observer.events == ["before_model", "after_model"]
assert result["messages"][-1].content == "Observed reply"
print("Hooks: before_model -> after_model")
print("Reply: Observed reply")
