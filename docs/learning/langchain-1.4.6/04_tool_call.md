<!--
File: docs/learning/langchain-1.4.6/04_tool_call.md
Purpose: Execute a local tool and handle invalid arguments.
Maintainer: sunshine-engineer
Modified: 2026-10-23
-->
# Execute a local tool and handle invalid arguments

**Content status:** authored by Codex; teaching draft; Sunny final approval pending.
**Example status:** see the [execution record](execution.json) for the tested code,
dependency set, date and outcome. Model messages are scripted; the tool runs for real.

## Outline

1. When and why to register a tool.
2. Complete example and expected output.
3. Invalid arguments and common mistakes.
4. What this verifies and source mapping.

## When and why

Register a tool when an agent needs a Python operation rather than a text-only
response. Here, `add` is deliberately small so you can inspect the complete cycle:
a scripted AI tool request, actual Python execution, a tool result, and a final AI
message. Passing `tools=[add]` registers a list containing the tool.

The fake model needs a fixture-only `bind_tools` adapter because its responses
already contain tool calls. Returning `self` here does not implement a production
provider adapter. An actual model must support the tool-calling protocol.

## Complete example

Follow the [exact environment setup](README.md#environment-and-execution), then run:

```bash
python examples/learning/langchain_1_4_6/04_tool_call.py
```

```python
# File: examples/learning/langchain_1_4_6/04_tool_call.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Execute a local tool using scripted model messages; no provider inference."""

from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool


class ScriptedToolModel(FakeMessagesListChatModel):
    """Fixed-response test model that accepts tool binding without provider inference."""

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        # Fixture-only adapter: messages below already contain scripted tool calls.
        # This does not teach a model to select tools or validate provider support.
        """Return this scripted model unchanged so the offline tool example can construct
        an agent.

        Args:
            tools: Tool definitions accepted to satisfy the fake-model binding
                interface.
            tool_choice: Unused binding choice; this model emits a fixed scripted
                response.
            **kwargs: Keyword overrides forwarded to the wrapped API.

        Returns:
            This scripted model instance; no provider-side binding occurs.
        """
        return self


calls: list[tuple[int, int]] = []


@tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    calls.append((a, b))
    return a + b


def build_agent(arguments):
    """Construct a deterministic agent with a scripted tool request and final response.

    Args:
        arguments: Explicit command arguments or scripted tool arguments.

    Returns:
        Compiled agent using fixed messages and the real local add tool.
    """
    return create_agent(
        model=ScriptedToolModel(
            responses=[
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "add",
                            "args": arguments,
                            "id": "call-add",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="Scripted final reply"),
            ]
        ),
        tools=[add],
    )


result = build_agent({"a": 2, "b": 3}).invoke(
    {"messages": [{"role": "user", "content": "Add 2 and 3"}]}
)
assert [m.type for m in result["messages"]] == ["human", "ai", "tool", "ai"]
tool_message = result["messages"][2]
assert tool_message.content == "5"
assert tool_message.tool_call_id == "call-add"
assert tool_message.status == "success"
assert calls == [(2, 3)]
print("Executed tool: add(2, 3) = 5")
print("Message order: human -> ai -> tool -> ai")

# Invalid arguments should produce a tool error without running our function.
bad = build_agent({"a": "not-an-integer", "b": 3}).invoke(
    {"messages": [{"role": "user", "content": "Invalid tool arguments"}]}
)
error_message = bad["messages"][2]
assert error_message.type == "tool"
assert error_message.status == "error"
assert error_message.tool_call_id == "call-add"
assert calls == [(2, 3)], "Invalid arguments must not execute the Python function"
print("Invalid integer argument: tool error; function not executed")
```

Expected standard output:

```text
Executed tool: add(2, 3) = 5
Message order: human -> ai -> tool -> ai
Invalid integer argument: tool error; function not executed
```

The call log is important: a final answer containing “5” alone would not prove
that the Python function ran. Assertions verify the actual call, returned tool
content, tool-call ID, success status and message ordering.

## Common mistakes and failure case

- Register tools as a list, even when there is one tool. The annotated function
  and its docstring supply the tool interface in this example.
- Preserve the tool-call ID so a result can be associated with its request.
- Inspect tool status rather than treating a final AI reply as proof of success.
  The fixture emits its final reply even after the invalid call produces an error.
- Invalid integer input is checked before the Python function runs. The example
  asserts an error ToolMessage and verifies that the call log did not change.
- This validation does not authorize an operation or make arbitrary tool code
  safe. Keep real tools bounded and enforce permissions in the application.

## Verification limits and source mapping

This verifies local tool execution, message routing and one argument-validation
failure under the pinned dependencies. It does not verify an LLM's ability to
choose a tool, construct arguments, recover from an error or reason from a tool
result. There are no network calls or external side effects. The fixture's
`bind_tools` override ignores tool-choice configuration intentionally.

The [pinned official agent factory](https://github.com/langchain-ai/langchain/blob/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/factory.py)
is the source for the registered-tools interface and agent loop. The code and
expected results above are authored experiments, not upstream examples.

[Back to learning collection](README.md)
