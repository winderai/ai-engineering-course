# Agentic Systems

How to move beyond rigid, hard-coded workflows to build systems that can think, plan, and adapt.

## The Brittle Workflow Problem

Let's start with a real example. Show this rigid email processing workflow:

```bash
bat rigid_workflow.py
```

Run it and show how it breaks with unexpected inputs:

```bash
uv run python rigid_workflow.py
```

Point out the problems:

- Every edge case requires code changes
- Complex nested if-statements
- Fragile to new requirements
- Zero adaptability

---

## What Makes a System "Agentic"?

An agent has three key capabilities:

1. **Reasoning** - Can analyze situations and make decisions
2. **Planning** - Can break down complex tasks into steps
3. **Tool Usage** - Can leverage external capabilities

Let's see this in action with a simple ReAct pattern:

```bash
bat simple_agent.py
```

Run the agent:

```bash
uv run python simple_agent.py
```

Notice how it:

- Thinks through the problem step by step
- Chooses appropriate tools
- Adapts based on results

---

## Core Architecture: ReAct Pattern

ReAct (Reasoning + Acting) is the foundation of most agentic systems. Show the pattern:

1. **Observe** - What's the current situation?
2. **Think** - What should I do next?
3. **Act** - Execute an action
4. **Repeat** - Continue until goal is achieved

Let's build this step by step:

```bash
bat react_agent.py
```

---

## Advanced Planning Strategies

### Sequential Planning

**Why this matters:** Most business processes have natural step-by-step flows. Sequential planning helps agents maintain context between steps, avoid redundant work, and ensure dependencies are handled in the right order.

**Use cases:** Data processing pipelines, software deployment workflows, customer onboarding processes

Show a sequential planner that dynamically creates step-by-step plans:

```bash
bat sequential_planner.py
```

Run it to see dynamic planning in action:

```bash
uv run python sequential_planner.py
```

---

### Hierarchical Planning

**Why this matters:** Complex projects require breaking work into phases with dependencies. Hierarchical planning lets agents manage parallel workstreams while respecting prerequisites.

**Use cases:** Software architecture projects, marketing campaigns, research studies

For complex tasks, break into phases with dependency management:

```bash
bat hierarchical_planner.py
```

Run it to see hierarchical decomposition:

```bash
uv run python hierarchical_planner.py
```

---

### Self-Correcting Agents

**Why this matters:** Real-world systems fail. Self-correcting agents can detect failures, analyze root causes, and adapt their approach - reducing manual intervention and improving reliability.

**Use cases:** API integration, data quality pipelines, automated testing

Agents should handle failures gracefully and learn from mistakes:

```bash
bat self_correcting_agent.py
```

Run it to see failure recovery in action:

```bash
uv run python self_correcting_agent.py
```

---

## Multi-Agent Systems

Sometimes you need specialized agents working together:

```bash
bat multi_agent_system.py
```

Demonstrate coordination:

```bash
uv run python multi_agent_system.py
```

---

## Popular Frameworks and Tools

- [smolagents](https://huggingface.co/docs/smolagents/index)
- [pydanticai](https://ai.pydantic.dev/)

---

## Practical Exercise: Building a Research Agent

Let's build a practical research agent using PydanticAI with DuckDuckGo search and our local Ollama model:

```bash
bat smolagents_research.py
```

Run the research agent:

```bash
uv run python smolagents_research.py
```

This demonstrates:

- Using smolagents framework with local Ollama models
- DuckDuckGo search tool integration
- Real web research capabilities

---

## Common Pitfalls and Best Practices

- Pitfall 1: Over-Engineering: Don't use agents for simple tasks.
- Pitfall 2: Infinite Loops: Always set max iterations.
- Pitfall 3: Poor Error Handling: Implement proper error boundaries.
- Pitfall 4: Cost Management: Monitor token usage and set budgets.
- Pitfall 5: Debugging: Use structured logging and distributed tracing.
- Pitfall 6: Guardrails: Use guardrails to prevent the agent from doing unsafe things.

---

## When to Use Agentic Systems

✅ **Good Use Cases:**

- Complex, multi-step workflows
- Dynamic decision-making required
- Many edge cases to handle
- Integration of multiple data sources
- Tasks requiring iteration and refinement

❌ **Poor Use Cases:**

- Simple, deterministic tasks
- Real-time, low-latency requirements
- Tasks with strict compliance needs
- When explainability is critical

---

## Summary and Next Steps

Key takeaways:

- Agents provide flexibility over hard-coded workflows
- Start with simple ReAct patterns
- Use native tool calling APIs
- Plan for error handling and cost management
- Choose the right tool for complexity level
