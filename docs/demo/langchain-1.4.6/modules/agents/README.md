> REVIEW-ONLY DRAFT — pending final content approval.

# langchain.agents

Package: `langchain==1.4.6`

[Table of contents](../../README.md)

## Purpose

langchain.agents is the entrypoint for building LangChain agents.

> Entrypoint to building \[Agents\](https://docs.langchain.com/oss/python/langchain/agents) with LangChain.
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/__init__.py)

## Public exports

The module publicly exports AgentState and create_agent through __all__.

> __all__ = \[
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/__init__.py)

> "AgentState",
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/__init__.py)

> "create_agent",
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/__init__.py)

## Import origins

create_agent is imported from langchain.agents.factory; AgentState comes from langchain.agents.middleware.types.

> from langchain.agents.factory import create_agent
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/__init__.py)

> from langchain.agents.middleware.types import AgentState
[Official source](https://raw.githubusercontent.com/langchain-ai/langchain/84ba23c414eca6bf6f6ebd1394a3006378113540/libs/langchain_v1/langchain/agents/__init__.py)


## Pages in this module

- [create_agent](functions/create-agent.md)
- [AgentMiddleware](classes/agent-middleware.md)
