# LLM Model Routing & Selection

Smart model routing optimizes cost and performance by directing requests to the most appropriate model. Instead of using a single expensive model for all tasks, route requests based on complexity, urgency, and quality requirements.

Why? Latency and cost.

---

Typically we don't use LLM's for this task. Train your own model. E.g. RLHF from feedback.

But... We can demo with an LLM and a prompt.

---

## 1. Complexity-Based Routing

Route requests based on task difficulty:

```bash
curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen3:0.6b",
  "prompt": "Classify if this email needs escalation to a team leader. Respond `{\"escalate\": true}` if the email:\n- Asks questions about products/services\n- Reports problems or complaints\n- Requests specific information\n- Needs technical or detailed responses. Respond `{\"escalate\": false} if the email:\n- Is simple feedback or praise\n- Contains basic greetings\n- Makes general comments\n- Requires only acknowledgment</rule>\n\nFor example:\n- i love your beer → NO\nIs your beer gluten free? → YES\nGreat service! → NO\nWhat are your hours? → YES\nMy order is wrong → YES\n\n<email>I love your beer!</email>\nResponse: ",
  "options": {"num_predict": 10},
  "stream": false,
  "think": false,
  "options": {
    "temperature": 0.01
  }
}' | jq -r '.response'
```

---

```bash
curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen3:0.6b",
  "prompt": "Classify if this email needs escalation to a team leader. Respond `{\"escalate\": true}` if the email:\n- Asks questions about products/services\n- Reports problems or complaints\n- Requests specific information\n- Needs technical or detailed responses. Respond `{\"escalate\": false} if the email:\n- Is simple feedback or praise\n- Contains basic greetings\n- Makes general comments\n- Requires only acknowledgment</rule>\n\nFor example:\n- i love your beer → NO\nIs your beer gluten free? → YES\nGreat service! → NO\nWhat are your hours? → YES\nMy order is wrong → YES\n\n<email>Is your beer gluten free?</email>\nResponse: ",
  "options": {"num_predict": 10},
  "stream": false,
  "think": false,
  "options": {
    "temperature": 0.01
  }
}' | jq -r '.response'
```

---

## Others

1. Task-based manual routing
2. SLA-based routing
3. Latency-based routing
4. Cost-based routing
5. Load-based routing
6. Feedback-based routing
