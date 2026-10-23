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
