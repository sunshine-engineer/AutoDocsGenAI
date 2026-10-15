# AgentMiddleware

Package: `langchain==1.4.6`

[Table of contents](../../../README.md)

## Purpose and subclassing

AgentMiddleware is the base class to subclass when customizing behavior between steps in the agent loop.

> Base middleware class for an agent.
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/middleware/types.py)

> between steps in the main agent loop.
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/middleware/types.py)

## Agent lifecycle hooks

before_agent runs logic before agent execution starts; after_agent runs logic after it completes.

> Logic to run before the agent execution starts.
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/middleware/types.py)

> Logic to run after the agent execution completes.
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/middleware/types.py)

## Model lifecycle hooks

before_model and after_model run logic before and after a model call. Their documented return values are state updates to apply at the corresponding stage.

> Agent state updates to apply before model call.
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/middleware/types.py)

> Agent state updates to apply after model call.
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/middleware/types.py)

## Model and tool wrappers

wrap_model_call intercepts model execution through a handler callback. wrap_tool_call intercepts tool execution for retries, monitoring, or modification.

> Intercept and control model execution via handler callback.
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/middleware/types.py)

> Intercept tool execution for retries, monitoring, or modification.
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/middleware/types.py)

