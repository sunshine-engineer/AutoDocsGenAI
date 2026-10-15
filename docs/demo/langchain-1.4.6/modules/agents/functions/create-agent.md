> REVIEW-ONLY DRAFT — pending final content approval.

# create_agent

Package: `langchain==1.4.6`

[Table of contents](../../../README.md)

## Purpose and result

create_agent builds an agent graph that calls tools in a loop. It returns a compiled StateGraph for chat interactions.

> Creates an agent graph that calls tools in a loop until a stopping condition is met.
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/factory.py)

> A compiled `StateGraph` that can be used for chat interactions.
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/factory.py)

## Key inputs

model selects the language model; tools supplies the tools list; system_prompt optionally supplies the system message.

> model: The language model for the agent.
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/factory.py)

> tools: A list of tools, `dict`, or `Callable`.
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/factory.py)

> system_prompt: An optional system prompt for the LLM.
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/factory.py)

## Tool-call loop

When the model produces tool_calls, the graph executes tools and adds their ToolMessage responses. The cycle repeats until the model response contains no more tool_calls.

> contains `tool_calls`, the graph will then call the tools.
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/factory.py)

> The tools node executes
> the tools and adds the responses to the messages list as
> \[`ToolMessage`\]\[langchain.messages.ToolMessage\] objects.
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/factory.py)

> until no more `tool_calls` are present
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/factory.py)

## Conversation persistence

A checkpointer persists graph state for a single conversation thread. A store persists data across multiple threads; this distinction concerns conversations, not CPU threading.

> Used for persisting the state of the graph
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/factory.py)

> single thread (e.g., a single conversation).
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/factory.py)

> Used for persisting data across multiple threads
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/factory.py)

