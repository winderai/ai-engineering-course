#!/usr/bin/env python3
import mlflow
from mlflow.tracking import MlflowClient

# Configure MLflow
mlflow.set_tracking_uri("http://127.0.0.1:8080")
client = MlflowClient()


def setup_deployment_aliases():
    """Demonstrate prompt aliasing for deployment stages"""

    # For this demo, we'll work with known version numbers
    # In a production environment, you'd query the prompt registry
    print("🔍 Setting up deployment aliases for customer_service_prompt...")

    # Assume we have at least 2 versions from the registry demo
    latest_version = 2  # Enhanced version
    stable_version = 1  # Basic version

    try:
        # Set aliases using the correct prompt aliasing API
        mlflow.genai.set_prompt_alias(
            name="customer_service_prompt", alias="production", version=stable_version
        )

        mlflow.genai.set_prompt_alias(
            name="customer_service_prompt", alias="staging", version=latest_version
        )

        mlflow.genai.set_prompt_alias(
            name="customer_service_prompt", alias="development", version=latest_version
        )

        print("✅ Deployment Aliases Set:")
        print(f"   Production: v{stable_version} (stable, basic version)")
        print(f"   Staging: v{latest_version} (latest, enhanced version)")
        print(f"   Development: v{latest_version} (latest, enhanced version)")

        return {
            "production": stable_version,
            "staging": latest_version,
            "development": latest_version,
        }

    except Exception as e:
        print(f"❌ Error setting aliases: {str(e)}")
        print("Note: This may be due to prompt registry configuration.")

        # Fallback approach - demonstrate the concept
        print("\n📝 Demonstrating alias concept (simulated):")
        print(f"   Production: v{stable_version} (stable, basic version)")
        print(f"   Staging: v{latest_version} (latest, enhanced version)")
        print(f"   Development: v{latest_version} (latest, enhanced version)")

        return {
            "production": stable_version,
            "staging": latest_version,
            "development": latest_version,
        }


def load_prompt_by_environment(environment="production"):
    """Load prompt template by environment alias"""

    try:
        # Load prompt using alias
        prompt_uri = f"prompts:/customer_service_prompt@{environment}"
        prompt_template = mlflow.genai.load_prompt(prompt_uri)

        print(f"✅ Loaded {environment} prompt:")
        print(f"Template preview: {prompt_template.template[:100]}...")

        return prompt_template

    except Exception as e:
        print(f"❌ Error loading {environment} prompt: {str(e)}")

        # Fallback: try loading by version number
        try:
            # For demo purposes, map environments to version numbers
            version_map = {"production": 1, "staging": 2, "development": 2}
            version = version_map.get(environment, 1)

            prompt_uri = f"prompts:/customer_service_prompt/{version}"
            prompt_template = mlflow.genai.load_prompt(prompt_uri)

            print(f"✅ Loaded {environment} prompt (by version {version}):")
            print(f"Template preview: {prompt_template.template[:100]}...")

            return prompt_template

        except Exception as e2:
            print(f"❌ Fallback also failed: {str(e2)}")
            print(
                "Note: This may be due to prompt registry configuration or missing prompts."
            )
            return None


if __name__ == "__main__":
    aliases = setup_deployment_aliases()

    # Demo loading different environments
    for env in ["production", "staging", "development"]:
        print(f"\n=== Loading {env.upper()} Environment ===")
        load_prompt_by_environment(env)
