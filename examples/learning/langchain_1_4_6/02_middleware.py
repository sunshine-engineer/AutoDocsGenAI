"""Observe synchronous model calls without changing the conversation state."""

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage


class ObserveModel(AgentMiddleware):
    def __init__(self):
        self.events: list[str] = []

    def before_model(self, state, runtime):
        self.events.append("before_model")

    def after_model(self, state, runtime):
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
