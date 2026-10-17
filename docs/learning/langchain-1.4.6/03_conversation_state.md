# Retain a conversation and isolate another one

**Content status:** authored by Codex; teaching draft; Sunny final approval pending.
**Example status:** see the [execution record](execution.json) for the recorded result and hashes. No live provider calls.

## Outline

1. When and why to use it.
2. Complete example and expected output.
3. Common mistakes and verification limits.
4. Source mapping.

## When and why

Use a checkpointer when later invocations should retain graph state for a conversation. `InMemorySaver` is useful for a local demonstration where losing state when the process ends is acceptable.

The same `thread_id` identifies the conversation across two calls. Send only the new user message on the second call; the saver retains earlier messages. A different ID gets a separate history. Here “thread” means conversation identity, not CPU threading.

The fixture does not read or reason over the previous messages. Assertions verify stored history and isolation, not semantic memory.

## Run it

Follow the [exact environment setup](README.md#environment-and-execution), then run:

```bash
python examples/learning/langchain_1_4_6/03_conversation_state.py
```

This is the complete file, not a fragment requiring hidden helper code:

```python
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
```

Expected standard output:

```text
Same conversation: 2 -> 4 messages
Separate conversation: 2 messages
Missing thread configuration: rejected
```

Assertions check the scenario before printing success. The collection runner also compares this output exactly and rejects drift between the code above and its executable file.

## Common mistakes and limits

- Pass `config={"configurable": {"thread_id": ...}}` with checkpointed invocations. The final assertion demonstrates rejection when that configuration is missing.
- Reusing an ID intentionally shares a conversation history. A public service must control ownership and authorization rather than trusting arbitrary client-provided IDs.
- An in-memory saver does not prove disk persistence, restart recovery or cross-process sharing.
- A store for cross-thread data is a different capability; this example does not use one.

The separate conversation receives the next fixture response because the fake model's response sequence is shared. This does not indicate that conversation history leaked.

## Source mapping

The [pinned official implementation](https://github.com/langchain-ai/langchain/blob/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/factory.py) supports the API and lifecycle explanation. The code and expected results here are author-written experiments, not copied upstream examples. Execution verifies the listed scenario with the dependency set in the report; it does not establish all possible behavior of this API.

[Back to learning collection](README.md)
