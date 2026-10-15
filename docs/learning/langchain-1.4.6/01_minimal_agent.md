# Invoke an agent without a provider account

**Content status:** authored by Codex; teaching draft; Sunny final approval pending.
**Example status:** see the [execution record](execution.json) for the recorded result and hashes. No live provider calls.

## Outline

1. When and why to use it.
2. Complete example and expected output.
3. Common mistakes and verification limits.
4. Source mapping.

## When and why

Use `create_agent` when you want the agent graph interface without constructing its nodes yourself. In this recipe, a fixed-response model lets you learn the input and result structure before introducing provider credentials, model variability or tools.

The input contains one user message. The result contains the user message and one AI response. The reply is supplied by the fixture: this does not show that a language model understood the request or followed instructions.

## Run it

Follow the [exact environment setup](README.md#environment-and-execution), then run:

```bash
python examples/learning/langchain_1_4_6/01_minimal_agent.py
```

This is the complete file, not a fragment requiring hidden helper code:

```python
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
```

Expected standard output:

```text
Reply: Hello, Sunny!
Messages: 2
```

Assertions check the scenario before printing success. The collection runner also compares this output exactly and rejects drift between the code above and its executable file.

## Common mistakes and limits

- Read the last message's `content`; the result is a state dictionary, not a plain response string.
- A fixed-response model proves wiring only. Do not use its success to claim answer quality or tool-calling support.
- Keep distinct message objects for distinct turns; message identity can affect how history is merged.

Try changing the fixture reply and its assertion together. Changing only the user question will not make this fixture reason about it.

## Source mapping

The [pinned official implementation](https://github.com/langchain-ai/langchain/blob/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/factory.py) supports the API and lifecycle explanation. The code and expected results here are author-written experiments, not copied upstream examples. Execution verifies the listed scenario with the dependency set in the report; it does not establish all possible behavior of this API.

[Back to learning collection](README.md)
