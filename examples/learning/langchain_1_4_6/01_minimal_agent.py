"""Minimal agent invocation: fixed model output, no tools or provider calls."""

from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

agent = create_agent(
    model=FakeMessagesListChatModel(responses=[AIMessage(content="Hello, Sunny!")]),
    tools=[],
)
result = agent.invoke({"messages": [{"role": "user", "content": "Say hello"}]})
assert [message.type for message in result["messages"]] == ["human", "ai"]
assert result["messages"][-1].content == "Hello, Sunny!"
print("Reply: Hello, Sunny!")
print("Messages: 2")
