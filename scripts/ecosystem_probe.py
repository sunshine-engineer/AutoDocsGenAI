# File: scripts/ecosystem_probe.py
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
"""Offline runtime contracts; run inside an isolated, exactly pinned environment."""

from __future__ import annotations

import importlib.metadata
import json
import sys
from pathlib import Path
from typing import TypedDict


def run() -> dict:
    """Execute independent offline compatibility probes and return their outcomes.

    Returns:
        dict: Execute independent offline compatibility probes and return their
            outcomes.
    """
    checks = []

    def check(name, callback):
        """Run one compatibility callback and record a passed or failed result.

        Args:
            name: Field, distribution or check name for this operation.
            callback: Callable implementing one isolated offline probe.
        """
        try:
            detail = callback()
            checks.append({"name": name, "status": "passed", "detail": detail})
        except Exception as error:  # noqa: BLE001
            checks.append(
                {
                    "name": name,
                    "status": "failed",
                    "error": f"{type(error).__name__}: {error}",
                }
            )

    def chain():
        """Execute a prompt/fake-model/parser chain and verify its offline result.

        Returns:
            Description of the verified offline runnable-chain behavior.
        """
        from langchain_core.language_models.fake_chat_models import FakeListChatModel
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages([("human", "{question}")])
        result = (
            prompt
            | FakeListChatModel(responses=["verified offline"])
            | StrOutputParser()
        ).invoke({"question": "test"})
        assert result == "verified offline", result
        return "Prompt -> fake chat model -> output parser executed"

    def graph():
        """Verify conditional routing, in-memory checkpoints and graph streaming offline.

        Returns:
            Description of the verified routing, checkpoint and streaming behavior.
        """
        from langchain_core.runnables import RunnableConfig
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.graph import END, START, StateGraph

        class State(TypedDict):
            """Typed integer state for the offline routing/checkpoint compatibility probe.

            Attributes:
                value (int): Value to normalize or validate under this function
                    contract.
            """

            value: int

        builder = StateGraph(State)
        builder.add_node("increment", lambda state: {"value": state["value"] + 1})
        builder.add_edge(START, "increment")
        builder.add_conditional_edges(
            "increment",
            lambda state: "again" if state["value"] < 2 else "done",
            {"again": "increment", "done": END},
        )
        app = builder.compile(checkpointer=InMemorySaver())
        config: RunnableConfig = {"configurable": {"thread_id": "offline-contract"}}
        result = app.invoke({"value": 0}, config)
        assert result["value"] == 2, result
        assert app.get_state(config).values["value"] == 2
        events = list(app.stream({"value": 1}, config))
        assert events, "stream empty"
        return "StateGraph conditional routing, checkpoint state and streaming executed"

    def tools():
        """Test direct ToolNode invocation and report version-specific runtime failures.

        Returns:
            Description of the verified direct ToolNode behavior.
        """
        from langchain_core.messages import AIMessage
        from langchain_core.tools import tool
        from langgraph.prebuilt import ToolNode

        @tool
        def add(a: int, b: int) -> int:
            """Add two integers."""
            return a + b

        node = ToolNode([add])
        result = node.invoke(
            {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "add",
                                "args": {"a": 2, "b": 3},
                                "id": "call-test",
                                "type": "tool_call",
                            }
                        ],
                    )
                ]
            }
        )
        assert result["messages"][0].content == "5", result
        return "Tool schema and actual local ToolNode execution returned 5"

    def graph_tools():
        """Execute a scripted tool call inside a compiled graph with runtime context.

        Returns:
            Description of the verified compiled-graph tool behavior.
        """
        from langchain_core.messages import AIMessage
        from langchain_core.tools import tool
        from langgraph.graph import END, START, MessagesState, StateGraph
        from langgraph.prebuilt import ToolNode

        @tool
        def add(a: int, b: int) -> int:
            """Add two integers."""
            return a + b

        builder = StateGraph(MessagesState)
        builder.add_node("tools", ToolNode([add]))
        builder.add_edge(START, "tools")
        builder.add_edge("tools", END)
        result = builder.compile().invoke(
            {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "add",
                                "args": {"a": 2, "b": 3},
                                "id": "graph-call",
                                "type": "tool_call",
                            }
                        ],
                    )
                ]
            }
        )
        assert result["messages"][-1].content == "5"
        return "ToolNode executed inside compiled StateGraph with runtime context"

    def agent():
        """Construct and invoke create_agent with a fixed-response model and no tools.

        Returns:
            Description of the verified offline agent invocation.
        """
        from langchain.agents import create_agent
        from langchain_core.language_models.fake_chat_models import FakeListChatModel

        app = create_agent(FakeListChatModel(responses=["agent verified"]), tools=[])
        result = app.invoke({"messages": [{"role": "user", "content": "test"}]})
        assert result["messages"][-1].content == "agent verified"
        return "create_agent constructed and invoked with a fake model"

    check("runnable_chain", chain)
    check("state_graph_checkpoint_stream", graph)
    check("local_tool_node", tools)
    check("graph_tool_node", graph_tools)
    check("modern_create_agent", agent)
    return {
        "python": sys.version,
        "distributions": {
            dist.metadata["Name"]: dist.version
            for dist in importlib.metadata.distributions()
        },
        "checks": checks,
        "limits": "No external LLM, vector database, cloud credentials, provider network calls or exhaustive examples tested.",
    }


if __name__ == "__main__":
    output = Path(sys.argv[1])
    output.write_text(json.dumps(run(), indent=2), encoding="utf-8")
    print(output.read_text())
