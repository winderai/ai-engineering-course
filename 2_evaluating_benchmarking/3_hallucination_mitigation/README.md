# Hallucination Mitigation Techniques

Hallucinations occur when AI models generate information that isn't grounded in their training data or the provided context. Today we'll explore practical techniques to detect and reduce these hallucinations.

---

## Understanding Hallucinations

Let's start by seeing a hallucination in action:

```bash
# Ask about a made-up person
ollama run qwen3:1.7b --think=false "Tell me about Dr. Samantha Rodriguez, the Nobel Prize winner in AI from 2025"
```

The model will likely provide detailed information about this fictional person. This is a hallucination - the model is generating plausible-sounding but false information.

---

## Technique 1: Explicit Uncertainty Instructions

The simplest mitigation is instructing the model to express uncertainty:

```bash
# Without uncertainty instruction
ollama run qwen3:1.7b --think=false "What is the population of Atlantis?"

# With uncertainty instruction
ollama run qwen3:1.7b --think=false "What is the population of Atlantis? If you don't know or if the information doesn't exist, say 'I don't have that information'"
```

---

## Technique 2: Self-Verification Prompts

We can ask the model to verify its own statements:

```bash
# Create a self-verification prompt
cat << 'EOF' | ollama run qwen3:1.7b --think=false
Task: Answer the following question, then verify your answer.

Question: What year did the company OpenAI release GPT-5?

Instructions:
1. First think about your answer
2. Then ask yourself: "Is this information factual or could I be making this up?"
3. If uncertain, revise your answer to indicate uncertainty
EOF
```

---

## Technique 3: Citation Requirements

Requiring citations helps ground responses:

```bash
# Ask for information with citation requirement
cat << 'EOF' | ollama run qwen3:1.7b --think=false
List three benefits of quantum computing. For each benefit, indicate if this is:
- Well-established fact
- Current research area
- Theoretical possibility
- Unknown/Speculative
EOF
```

---

## Technique 4: Confidence prediction

We've already seen this in the previous section.

---

## Technique 5: Chain-of-Thought Verification

Breaking down complex claims into verifiable steps:

```bash
# Create a chain-of-thought verification
cat << 'EOF' | ollama run qwen3:1.7b --think=false
Claim: "Coffee was invented in Italy in the 15th century"

Please verify this claim step by step:
1. Break down the key facts in this claim
2. What do I know about each fact?
3. Are there any contradictions or uncertainties?
4. What is my confidence level?
5. Final verdict: Is the claim accurate?

Provide your analysis for each step.
EOF
```

---

## Comparing Temperatures for Factual Accuracy

Temperature affects hallucination likelihood:

```bash
echo "-------------------------------------"
# High temperature (more creative, more hallucinations)
curl -s http://localhost:11434/api/generate \
  -d '{
    "model": "qwen3:1.7b",
    "prompt": "Coffee was invented in Italy in the 15th century",
    "stream": false,
    "think": false,
    "options": {
      "temperature": 0.1,
      "num_predict": 100
    }
  }' | jq -r '.response'

echo "---"

# Low temperature (more conservative, fewer hallucinations)
curl -s http://localhost:11434/api/generate \
  -d '{
    "model": "qwen3:1.7b",
    "prompt": "Coffee was invented in Italy in the 15th century",
    "stream": false,
    "think": false,
    "options": {
      "temperature": 2,
      "num_predict": 100
    }
  }' | jq -r '.response'
```

---

## Key Takeaways

1. **Always instruct models to express uncertainty** when they don't know something
2. **Use structured outputs** with confidence scores for factual claims
3. **Lower temperature** reduces hallucinations for factual tasks
4. **Self-verification prompts** help models catch their own errors
5. **Citation requirements** ground responses in verifiable information
