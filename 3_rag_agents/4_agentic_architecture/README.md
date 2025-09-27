# Agentic Architecture and Design Patterns

> Who here has tried to build an AI agent that could handle *everything*?

## Core Concept: The No Free Lunch Theorem Applied

**Key Point:** There is no perfect agent for all tasks. This is an extension of the No Free Lunch Theorem from machine learning.

- This isn't a limitation - it's a design principle
- Python isn't better than C++ in all scenarios
- This drives us toward specialized architectural patterns

**Practical Implication:** Instead of building one mega-agent, we design specific architectures for specific use cases.

---

## The Two Fundamental Patterns

### Pattern 1: The Continuous Loop (Reinforcement Learning-Based)

**Structure:**

- Observation of current environment
- Available actions
- Reward signal

**When to Use:** Complex, non-linear tasks with multiple competing actions

**Real-World Example:** A debugging agent that needs to:

1. Analyze error logs
2. Form hypotheses
3. Test solutions
4. Iterate based on results

---

### Pattern 2: Pipeline/Workflow

**Structure:** Sequential, predefined steps with clear inputs and outputs

**When to Use:** Linear processes that humans would naturally break into distinct steps

**Real-World Example:** Email processing system:

1. Parse incoming email
2. Classify content type
3. Extract relevant data
4. Route to appropriate handler
5. Generate response

---

## Decision Framework: Loop vs Pipeline

Ask yourself: "How would a human expert approach this task?"

**Choose Pipeline if:**

- Steps are highly linear
- Process follows distinct stages
- Each step has clear inputs/outputs
- Failure modes are predictable

**Choose Loop if:**

- Strategy involves competing actions
- Non-linear problem solving required
- Context heavily influences next steps
- Adaptation is crucial

---

## Case Study Deep Dive

### Aider: The Architect/Editor Pattern

**Architecture Overview:**

1. **Architect** (expensive, powerful model): Designs and plans
2. **Editor** (fast, specialized model): Implements changes

**Key Insights:**

- Achieves 85% on code editing benchmarks (state-of-the-art)
- Context isolation: Editor doesn't receive full architect context
- Different models for different strengths

**Discussion Points:**

- How does context limitation help performance?
- What other domains could benefit from this split?
- Cost implications of hybrid model approaches

**Live Demo:** Show the actual prompts:

- [Architect prompt](https://github.com/Aider-AI/aider/blob/main/aider/coders/architect_prompts.py)
- [Multiple different editor prompts depending on the model](https://github.com/Aider-AI/aider/tree/main/aider/coders)
- [Direct edit blocks](https://github.com/Aider-AI/aider/blob/main/aider/coders/editblock_prompts.py#L7) vs functional [edit blocks](https://github.com/Aider-AI/aider/blob/main/aider/coders/editblock_func_coder.py)

---

### Cline: Human-in-the-Loop ReAct

**Architecture Overview:**

- Traditional looping agent with tool calling
- Human-controlled gates for oversight
- Everything modelled as one big prompt

**Key Insights:**

- Extension of ReAct architecture
- Human oversight at critical decision points
- Simpler but more dependent on human judgment
- Roo and other cline derivatives introduce aider-like modes.

**Live Demo:** Show the actual prompts:

```bash
bat cline-system-prompt.txt
```

---

## Advanced Concepts

### Planning Strategies

- **Linear planning:** Good for known processes
- **Hierarchical decomposition:** Break complex tasks into subtasks
- **Backtracking:** When plans fail, intelligently retreat
- **Parallel execution:** Multiple agents working simultaneously
- **Conditional and branching logic:** When to use different models for different tasks

---

### State Management Patterns

- **Context tracking:** Like Claude Code's todo lists
- **Memory systems:** Short-term vs long-term information
- **State persistence:** Surviving crashes and restarts
- **Shared state:** Multiple agents coordinating

---

### Human In The Loop

- Oversight at critical decision points
- Stakeholders want automation, users want control and visibility

---

### Other Topics

- Error handling strategy
- Tool calling patterns
- Cost management
- Debugging
- Guardrails
- Monitoring, logging, tracing
- Security
- Compliance
- Performance
- Scalability
