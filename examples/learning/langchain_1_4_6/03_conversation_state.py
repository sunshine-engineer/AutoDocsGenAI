"""Check same-thread retention and separate-thread isolation in memory."""

from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model=FakeMessagesListChatModel(
        responses=[
            AIMessage(content="Reply one"),
            AIMessage(content="Reply two"),
            AIMessage(content="Separate reply"),
        ]
    ),
    tools=[],
    checkpointer=InMemorySaver(),
)
thread_a: RunnableConfig = {"configurable": {"thread_id": "conversation-a"}}
thread_b: RunnableConfig = {"configurable": {"thread_id": "conversation-b"}}
first = agent.invoke(
    {"messages": [{"role": "user", "content": "First message"}]}, config=thread_a
)
second = agent.invoke(
    {"messages": [{"role": "user", "content": "Second message"}]}, config=thread_a
)
separate = agent.invoke(
    {"messages": [{"role": "user", "content": "Separate message"}]}, config=thread_b
)
assert len(first["messages"]) == 2
assert len(second["messages"]) == 4
assert len(separate["messages"]) == 2
assert [m.content for m in second["messages"]] == [
    "First message",
    "Reply one",
    "Second message",
    "Reply two",
]
assert [m.content for m in separate["messages"]] == [
    "Separate message",
    "Separate reply",
]
try:
    agent.invoke({"messages": [{"role": "user", "content": "Missing thread"}]})
except ValueError as error:
    assert "thread_id" in str(error), str(error)
else:
    raise AssertionError("A checkpointer must reject a missing thread configuration")
print("Same conversation: 2 -> 4 messages")
print("Separate conversation: 2 messages")
print("Missing thread configuration: rejected")
