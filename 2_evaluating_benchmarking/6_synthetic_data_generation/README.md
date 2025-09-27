# Synthetic Data Generation for Testing

When you lack sufficient real-world examples for testing, synthetic data generation becomes essential. Let's explore how to create realistic test datasets for email classification that work seamlessly with Promptfoo.

---

## Why Generate Synthetic Data?

Real-world data often has limitations:

- Insufficient edge cases
- Privacy concerns with actual emails
- Imbalanced class distributions
- Missing specific scenarios for testing

Synthetic data helps us:

- Create comprehensive test coverage
- Control data distribution
- Test rare scenarios
- Build reproducible benchmarks

---

## Demo: Generating Synthetic Email Classification Dataset

We'll use Ollama to generate synthetic emails across different categories for brewery operations.

### Step 1: Review the Generation Script

```bash
# View the synthetic data generator
bat 2_evaluating_benchmarking/6_synthetic_data_generation/generate_synthetic_dataset.py
```

This script:

- Defines 6 email categories (URGENT_ISSUE, SUPPLY_ORDER, SCHEDULE, CUSTOMER, MAINTENANCE, OTHER)
- Creates 5 different scenarios per category with varying characteristics
- Uses LiteLLM to generate realistic emails via Ollama
- Outputs data in Promptfoo-compatible JSON format

---

### Step 2: Generate Synthetic Dataset

```bash
# Run the generator
uv run 2_evaluating_benchmarking/6_synthetic_data_generation/generate_synthetic_dataset.py
```

This creates `synthetic_emails.json` with 30 test cases ready for evaluation (5 per category).

---

### Step 3: Evaluate with Promptfoo

```bash
bat 2_evaluating_benchmarking/6_synthetic_data_generation/synthetic_eval.yaml

# Run evaluation
promptfoo eval -c 2_evaluating_benchmarking/6_synthetic_data_generation/synthetic_eval.yaml

# View results
promptfoo view
```

---

### Step 4: Analyze Results

The evaluation will show:

- How well the model classifies synthetic emails
- Which categories are most challenging
- Performance across different scenario types

---

## Best Practices

1. **Start Small**: Generate a few examples first to validate your approach
2. **Iterate on Prompts**: Refine generation prompts based on output quality
3. **Mix Real and Synthetic**: Combine synthetic data with real examples when available
4. **Validate Categories**: Ensure generated emails truly match their labels
5. **Monitor Diversity**: Check that synthetic data covers the full problem space
6. **Version Control**: Track different synthetic dataset versions
7. **Document Limitations**: Note what scenarios synthetic data might miss

## Resources

- [Promptfoo docs](https://www.promptfoo.dev/docs/intro/)
