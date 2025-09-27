# Use Case: Classification

This section explores the use of LLMs for classification tasks. It begins to explore the art and difficuly associated with prompt engineering and demonstrates how altering the prompt affects performance. This is is a bash example that plays around with different tasks and prompts to highlight the importance of prompt engineering.

---

## 1. Introduction to LLM Classification

- **What is classification?** Categorizing inputs into predefined classes
- **Traditional vs LLM classification**:
  - Traditional: Requires training data, feature engineering
  - LLM: Zero-shot, few-shot capabilities with natural language
- **Common use cases**:
  - Sentiment analysis
  - Content moderation
  - Intent classification
  - Document categorization
- **Why prompt engineering matters**: Small changes, big impact

---

## 2. Basic Classification Setup

- **Environment preparation**:

```bash
# Check if Ollama is installed and running
ollama --version

# Pull the model we'll use for classification
ollama pull qwen3:1.7b
```

---

- **Basic classification prompt structure**:

```txt
Classify the following text as [POSITIVE/NEGATIVE/NEUTRAL]:
Text: [INPUT]
Classification:
```

- **Demo**: Simple sentiment classification with Ollama
- **Key concepts**: Prompt structure, consistency, output format

---

### 3. Prompt Engineering Fundamentals

#### Version 1: Basic Prompt

```bash
# Basic sentiment classification - works for clear cases
ollama run qwen3:1.7b --think=false "Classify the following text as POSITIVE, NEGATIVE, or NEUTRAL:
Text: This product is okay, nothing special.
Classification:"
```

---

**Common failures with basic prompts:**

```bash
# Example 1: Ambiguous language - may give inconsistent results
ollama run qwen3:1.7b --think=false "Classify the following text as POSITIVE, NEGATIVE, or NEUTRAL:
Text: I guess it's fine.
Classification:"
```

---

```bash
# Example 2: Sarcasm - often misclassified
ollama run qwen3:1.7b --think=false "Classify the following text as POSITIVE, NEGATIVE, or NEUTRAL:
Text: Amazing, another software update.
Classification:"
```

---

```bash
# Example 3: Mixed sentiment - unclear which aspect to focus on

ollama run qwen3:1.7b --think=false "Classify the following text as POSITIVE, NEGATIVE, or NEUTRAL:
Text: The product is amazing but delivery was slow.
Classification:"
```

---

```bash
# Example 4: Format inconsistency - may not follow expected output format

ollama run qwen3:1.7b --think=false "Classify the following text as POSITIVE, NEGATIVE, or NEUTRAL:
Text: Love this!
Classification:"

```

- **Issues demonstrated**: Ambiguous language, sarcasm detection, mixed sentiment, output format inconsistency

---

#### Version 2: Adding Examples (Few-shot)

```bash
# Few-shot learning with examples
ollama run qwen3:1.7b --think=false "Classify the following text as POSITIVE, NEGATIVE, or NEUTRAL:

Examples:
Text: I love this product! Amazing quality.
Classification: POSITIVE

Text: Terrible experience, would not recommend.
Classification: NEGATIVE

Text: The product works as expected.
Classification: NEUTRAL

Now classify:
Text: This product is okay, nothing special.
Classification:"
```

- **Impact demonstration**: Compare accuracy improvements

---

#### Version 3: Detailed Instructions

```bash
# Detailed instructions with context
ollama run qwen3:1.7b --think=false "You are a sentiment analysis expert. Classify the following text as POSITIVE, NEGATIVE, or NEUTRAL based on the overall emotional tone and customer satisfaction level.

Guidelines:
- POSITIVE: Expresses satisfaction, joy, approval, or recommendation
- NEGATIVE: Expresses dissatisfaction, anger, disappointment, or criticism  
- NEUTRAL: Factual statements without clear emotional sentiment
- Consider context and implied meaning, not just explicit words
- If mixed sentiment, classify based on the dominant tone

Text: This product is okay, nothing special.
Classification:"
```

- **Edge case handling**: How detailed prompts handle ambiguity

---

#### Version 4: Output Format Specification

```bash
# Structured output format
ollama run qwen3:1.7b --think=false "Classify the sentiment and provide your answer in this exact format:

Text: This product is okay, nothing special.

Classification: [POSITIVE/NEGATIVE/NEUTRAL]
Confidence: [High/Medium/Low]  
Reasoning: [Brief explanation]"
```

- **Consistency benefits**: Easier parsing and integration

---

### 4. Advanced Classification Scenarios

---

#### Multi-class Classification

- **Email categorization**: Spam, Important, Social, Updates, Promotions

Email categorization - basic version

```bash
  
ollama run qwen3:1.7b --think=false "Classify this email as: SPAM, IMPORTANT, SOCIAL, UPDATES, or PROMOTIONS

Email: Get 50% off your next purchase! Limited time offer.

Category:"

```

---

Email categorization - improved version with definitions

```bash
ollama run qwen3:1.7b --think=false "Classify this email into one category:

SPAM: Unsolicited, suspicious, or fraudulent emails
IMPORTANT: Work-related, financial, legal, or urgent personal matters
SOCIAL: Communications from social networks, friends, or family
UPDATES: Service notifications, newsletters from subscribed sources
PROMOTIONS: Marketing emails from legitimate businesses

Email: Get 50% off your next purchase! Limited time offer.
Category:"
```

- **Challenge areas**: Overlapping categories, subjective boundaries

---

#### Confidence Scoring

- **Adding confidence to classifications**:

You'd think this would work, but no.

```bash
ollama run qwen3:1.7b --think=false "Classify the sentiment and provide a confidence level:

Text: I think this product might be okay for some people. I'm very neutral about it.

Format: CLASSIFICATION (confidence: High/Medium/Low)
Where CLASSIFICATION is POSITIVE, NEGATIVE, or NEUTRAL"
```

---

```bash
ollama run qwen3:1.7b --think=false "Classify the sentiment and provide a confidence level.

Sentiment Guidelines:
- POSITIVE: Expresses satisfaction, joy, approval, or recommendation
- NEGATIVE: Expresses dissatisfaction, anger, disappointment, or criticism  
- NEUTRAL: Factual statements without clear emotional sentiment
- Consider context and implied meaning, not just explicit words
- If mixed sentiment, classify based on the dominant tone

Confidence Guidelines:
- HIGH if the classification is accurate.
- MEDIUM if the classification is uncertain.
- LOW if the classification is low quality.

Important: Evaluate sentiment and confidence independently.

Output format:
Classification: POSITIVE/NEGATIVE/NEUTRAL
Confidence: HIGH/MEDIUM/LOW
Explanation: ...

Now classify the following text:

I think this product might be okay for some people. I'm very neutral about it."
```

- **Use cases**: Filtering low-confidence predictions

---

### 5. Model Comparison

- **Same prompts across different models**:

```bash
ollama run qwen3:1.7b --think=false "Classify sentiment as POSITIVE, NEGATIVE, or NEUTRAL: This product is decent for the price."
ollama run qwen3:8b --think=false "Classify sentiment as POSITIVE, NEGATIVE, or NEUTRAL: This product is decent for the price."
ollama run deepseek-r1:1.5b --think=false "Classify sentiment as POSITIVE, NEGATIVE, or NEUTRAL: This product is decent for the price."
ollama run gemma3:1b --think=false "Classify sentiment as POSITIVE, NEGATIVE, or NEUTRAL: This product is decent for the price."
```

- **Model differences**: Response style, consistency, and capability
- **Model-specific strengths**: Where each model excels
