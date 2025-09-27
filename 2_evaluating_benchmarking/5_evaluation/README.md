# Evaluation

In this section we'll explore how to use Promptfoo to evaluate the performance of our models.

---

## Demo: Using Promptfoo for Email Classification

Now let's see how to use a proper evaluation framework. Promptfoo makes it easy to create systematic benchmarks with multiple test cases and consistent scoring.

### Step 1: Install Promptfoo

```bash
npm install -g promptfoo
```

---

### Step 2: Create Test Dataset

```bash
bat 2_evaluating_benchmarking/5_evaluation/simple.yaml
```

---

### Step 3: Run the Benchmark

```bash
# Run the evaluation
promptfoo eval -c 2_evaluating_benchmarking/5_evaluation/simple.yaml

# View results in web interface
promptfoo view
```

---

### Step 4: Advanced Configuration

For more sophisticated evaluation:

```bash
bat 2_evaluating_benchmarking/5_evaluation/advanced.yaml

```bash
promptfoo eval -c 2_evaluating_benchmarking/5_evaluation/advanced.yaml
```

```bash
promptfoo view
```

---

### Available Assertions

[Documentation for available assertions](https://www.promptfoo.dev/docs/configuration/expected-outputs/).

### Benefits of Using Promptfoo

1. **Systematic Testing**: Run multiple test cases consistently
2. **Multiple Prompts**: Compare different prompt strategies side-by-side  
3. **Built-in Metrics**: Accuracy, latency, cost tracking
4. **Custom Scoring**: Domain-specific evaluation logic
5. **CI/CD Integration**: Automated evaluation in your pipeline
6. **Web Interface**: Visual results and debugging

## Resources

- [Winder.AI Overview of evaluation frameworks](https://winder.ai/testing-evaluating-large-language-models-ai-applications/)
