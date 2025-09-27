# Feedback Loops in AI Systems

Complete RLHF pipeline from thumbs up/down feedback to actual model training.

Full video investigating all feedback types: <https://winder.ai/user-feedback-llm-powered-applications/>

---

## Feedback Collection Types

**Inline Feedback** (thumbs up/down):

- Lightweight, familiar UI patterns
- High collection rates, minimal friction
- Implemented in thumbs_reward_demo.py

**Implicit Feedback** (user behavior):

- Copy actions indicate usefulness
- Time spent reading correlates with quality
- Edit patterns show improvement opportunities

**Differential Feedback** (A/B comparisons):

- Present multiple response options
- User selects preferred version
- Generates clean preference pairs

**Retrospective Feedback** (surveys):

- Holistic interaction assessment
- Captures systemic issues
- Net promoter score tracking

---

## Implementation Strategy

Focus on **continuous iteration** with user voice:

- Design feedback as product features, not afterthoughts
- Build data pipelines for collection → cleaning → training
- Monitor and A/B test improvements
- Keep users in context during feedback collection

---

## Demo 1: Train Reward Model from Preference Pairs

Show preference pairs format:

```bash
bat preference_data.json
```

Train reward model using TRL:

```bash
uv run python rlhf_demo.py
```

---

## Demo 2: Train from Thumbs Up/Down Data

Show realistic binary feedback data:

```bash
bat thumbs_feedback_data.json
```

Convert to preference pairs and train:

```bash
uv run python thumbs_reward_demo.py
```

---

## Demo 3: Complete PPO Training Pipeline

Use trained reward model for reinforcement learning:

```bash
uv run python ppo_training_demo.py
```

---

## Training Flow

1. **Collect feedback** → thumbs up/down from users
2. **Create preference pairs** → group by prompt, pair positive/negative
3. **Train reward model** → learn to score response quality
4. **PPO training** → use reward model to improve LLM responses

## Resources

- <https://winder.ai/user-feedback-llm-powered-applications/>
- <https://huggingface.co/docs/transformers/index>
- <https://huggingface.co/docs/peft/en/index>
- <https://huggingface.co/docs/trl/index>
