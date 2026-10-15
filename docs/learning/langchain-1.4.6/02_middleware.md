# Observe the model step with middleware

**Content status:** authored by Codex; teaching draft; Sunny final approval pending.
**Example status:** see the [execution record](execution.json) for the recorded result and hashes. No live provider calls.

## Outline

1. When and why to use it.
2. Complete example and expected output.
3. Common mistakes and verification limits.
4. Source mapping.

## When and why

Use `AgentMiddleware` when you need logic around steps in an agent, such as observing when model calls happen. Subclass it and pass an instance in `middleware=[...]`.

Here, `before_model` and `after_model` append event names to a list. The hooks observe the call and return no state updates. This keeps the example focused on hook order rather than changing messages. The list is a local teaching aid, not a production telemetry implementation.

## Run it

Follow the [exact environment setup](README.md#environment-and-execution), then run:

```bash
python examples/learning/langchain_1_4_6/02_middleware.py
```

This is the complete file, not a fragment requiring hidden helper code:

```python
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
```

Expected standard output:

```text
Hooks: before_model -> after_model
Reply: Observed reply
```

Assertions check the scenario before printing success. The collection runner also compares this output exactly and rejects drift between the code above and its executable file.

## Common mistakes and limits

- Implement the hooks appropriate to synchronous invocation; this example does not validate async hooks.
- A model hook runs around a model call. An agent that calls a model multiple times may produce multiple hook pairs.
- `before_agent` and `before_model` are different lifecycle boundaries; choose the boundary that matches the behavior you want.
- Do not log complete user messages or secrets just to observe hook execution. The example records only event names.

Use a fresh observer for independent experiments: this list accumulates events.

## Source mapping

The [pinned official implementation](https://github.com/langchain-ai/langchain/blob/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/middleware/types.py) supports the API and lifecycle explanation. The code and expected results here are author-written experiments, not copied upstream examples. Execution verifies the listed scenario with the dependency set in the report; it does not establish all possible behavior of this API.

[Back to learning collection](README.md)
