# Prompt Management & Version Control

Production prompt management requires systematic versioning, testing, and deployment. Let's build a complete MLflow-based prompt management system.

## Demo 1: Setting up MLflow for Prompt Management

First, install and start MLflow with the new prompt registry features:

```bash
# Install MLflow with all dependencies
uv add mlflow[extras]

# Start MLflow server with prompt registry enabled
uv run mlflow server --host 127.0.0.1 --port 8080 --backend-store-uri sqlite:///mlflow.db

# Wait for server to start
sleep 5
echo "MLflow UI available at: http://127.0.0.1:8080"
```

---

Create our first prompt management script:

```bash
bat 4_deployment/1_prompt_management/prompt_registry_demo.py
```

Run the prompt registration:

```bash
uv run python 4_deployment/1_prompt_management/prompt_registry_demo.py
```

---

## Demo 2: Prompt Aliasing and Deployment Pipeline

Create a deployment pipeline with aliases for different environments:

```bash
bat 4_deployment/1_prompt_management/prompt_deployment.py
```

Run the deployment setup:

```bash
uv run python 4_deployment/1_prompt_management/prompt_deployment.py
```

---

## Demo 4: Prompt Evaluation and A/B Testing

Create an evaluation framework for comparing prompt performance:

```bash
bat 4_deployment/1_prompt_management/prompt_evaluation.py
```

Run the evaluation:

```bash
uv run python 4_deployment/1_prompt_management/prompt_evaluation.py
```

---

## Demo 5: DSPy Integration for Prompt Optimization

Show how to use DSPy for systematic prompt optimization:

```bash
# Install DSPy
uv add dspy-ai

bat 4_deployment/1_prompt_management/dspy_optimization.py
```

Run DSPy optimization:

```bash
uv run python 4_deployment/1_prompt_management/dspy_optimization.py
```

---

## Key Takeaways

- **MLflow Prompt Registry** provides complete lifecycle management for prompts
- **Version control and lineage** tracking prevents prompt drift and enables rollbacks
- **Aliases enable deployment pipelines** - dev/staging/production environments
- **Team collaboration** through shared registries and review workflows
- **A/B testing and evaluation** ensure prompt performance before deployment
- **DSPy integration** enables systematic prompt optimization
- **Production monitoring** tracks prompt performance and user satisfaction
- **Structured approach** beats ad-hoc prompt management for serious applications
