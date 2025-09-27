#!/usr/bin/env python3
import mlflow

# Configure MLflow
mlflow.set_tracking_uri("http://127.0.0.1:8080")


def demo_prompt_registration():
    """Demonstrate prompt version control and lineage tracking"""

    # Version 1: Basic customer service prompt
    prompt_v1 = """
    You are a helpful customer service representative for TechCorp.

    Customer Query: {customer_query}

    Respond professionally and helpfully. If you cannot answer, direct them to support@techcorp.com.
    """

    # Register prompt version 1
    prompt_template_v1 = mlflow.genai.register_prompt(
        name="customer_service_prompt", template=prompt_v1
    )

    with mlflow.start_run(run_name="prompt_v1_registration"):
        mlflow.log_param("version", "1.0")
        mlflow.log_param("purpose", "basic customer service")
        mlflow.log_param("author", "prompt_engineer")

        # Log prompt information
        mlflow.log_param("prompt_uri", prompt_template_v1.uri)
        mlflow.log_param("prompt_version", prompt_template_v1.version)

        print(
            f"✅ Registered Prompt v1.0: {prompt_template_v1.name} (version {prompt_template_v1.version})"
        )

    # Version 2: Enhanced with context and constraints
    prompt_v2 = """
    You are a knowledgeable customer service representative for TechCorp, a software company.

    Context: Our main products are cloud analytics tools and mobile apps.
    Knowledge Base: Common issues include login problems, billing questions, and feature requests.

    Customer Query: {customer_query}

    Instructions:
    1. Respond professionally and empathetically
    2. For technical issues, provide step-by-step guidance
    3. For billing, direct to billing@techcorp.com
    4. For feature requests, acknowledge and mention our roadmap updates
    5. If unsure, say "Let me connect you with a specialist" and provide support@techcorp.com

    Response:
        """

    # Register prompt version 2 (update to existing prompt)
    prompt_template_v2 = mlflow.genai.register_prompt(
        name="customer_service_prompt", template=prompt_v2
    )

    with mlflow.start_run(run_name="prompt_v2_enhanced"):
        mlflow.log_param("version", "2.0")
        mlflow.log_param("purpose", "enhanced customer service with context")
        mlflow.log_param("author", "prompt_engineer")
        mlflow.log_param(
            "changes", "Added context, knowledge base, structured instructions"
        )

        # Simulate evaluation metrics
        mlflow.log_metric("helpfulness_score", 8.5)
        mlflow.log_metric("accuracy_score", 9.2)
        mlflow.log_metric("response_time_ms", 1200)
        mlflow.log_metric("user_satisfaction", 4.3)

        # Log prompt information
        mlflow.log_param("prompt_uri", prompt_template_v2.uri)
        mlflow.log_param("prompt_version", prompt_template_v2.version)

        print(
            f"✅ Registered Prompt v2.0: {prompt_template_v2.name} (version {prompt_template_v2.version})"
        )

    return prompt_template_v2


if __name__ == "__main__":
    demo_prompt_registration()
