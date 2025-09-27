#!/usr/bin/env python3
"""
MLflow Prompt Optimization with DSPy
=====================================

This module demonstrates how to use MLflow's optimize_prompt API with DSPy's
MIPROv2 algorithm for automatic prompt optimization using the ollama/qwen3:1.7b model.

This implementation performs actual prompt optimization using MLflow and DSPy.
To run successfully, ensure:
1. Ollama is running locally (ollama serve)
2. qwen3:1.7b model is available (ollama pull qwen3:1.7b)
3. MLflow dependencies are installed (pip install dspy>=2.6.0 mlflow>=3.1.0)
"""

from typing import Any, Dict
import pandas as pd
import mlflow
import mlflow.genai
import mlflow.data
from mlflow.genai.scorers import scorer
from mlflow.genai.optimize.types import OptimizerConfig, LLMParams

# Configure MLflow
mlflow.set_tracking_uri("http://127.0.0.1:8080")


@scorer
def response_quality(expectations: Dict[str, Any], outputs: Dict[str, Any]) -> int:
    """
    Scorer to evaluate if the response contains expected key information.
    This checks how many expected keywords are found in the output keywords.
    """
    expected_keywords = expectations.get("keywords", [])
    output_keywords = outputs.get("keywords", [])

    # Convert both to lowercase for comparison
    expected_lower = [kw.lower() for kw in expected_keywords]
    output_lower = (
        [kw.lower() for kw in output_keywords]
        if isinstance(output_keywords, list)
        else []
    )

    # Count how many expected keywords are found in the output
    score = sum(
        1 for kw in expected_lower if any(kw in out_kw for out_kw in output_lower)
    )

    return score


@scorer
def professionalism_check(outputs: Dict[str, Any]) -> int:
    """
    Scorer to check if the tone field indicates professionalism.
    """
    tone = outputs.get("tone", "").lower()
    keywords = outputs.get("keywords", [])

    # Professional tones get positive scores
    professional_tones = [
        "helpful",
        "professional",
        "polite",
        "courteous",
        "respectful",
    ]
    unprofessional_tones = ["rude", "angry", "dismissive", "harsh"]

    score = 0
    tone_score = 0
    keyword_score = 0

    # Check tone
    if any(prof_tone in tone for prof_tone in professional_tones):
        tone_score += 2
    if any(unprof_tone in tone for unprof_tone in unprofessional_tones):
        tone_score -= 2

    # Check keywords for professional indicators
    professional_keywords = ["help", "support", "assistance", "please", "thank you"]
    if isinstance(keywords, list):
        keyword_score = sum(
            1
            for kw in keywords
            if any(prof_kw in kw.lower() for prof_kw in professional_keywords)
        )

    score = tone_score + keyword_score
    final_score = max(0, score)  # Don't return negative scores

    return final_score


@scorer
def length_scorer(outputs: Dict[str, Any]) -> int:
    """
    Scorer to check the total length of keywords and tone fields.
    Returns a penalty for very long outputs.
    """
    keywords = outputs.get("keywords", [])
    tone = outputs.get("tone", "")

    # Calculate total length
    keywords_length = (
        sum(len(kw) for kw in keywords) if isinstance(keywords, list) else 0
    )
    tone_length = len(tone) if isinstance(tone, str) else 0
    total_length = keywords_length + tone_length

    # Return a penalty score (higher is worse, so we'll subtract this in objective)
    penalty = 0
    if total_length > 100:  # Too long
        penalty = 10
    elif total_length < 10:  # Too short
        penalty = 5
    else:
        penalty = 0  # Just right

    return penalty


@mlflow.trace
def setup_optimization_data():
    """
    Set up training and evaluation data for customer service prompt optimization.
    Uses MLflow datasets for better data lineage and tracking.
    """

    # Training data - used to optimize the prompt
    # Updated to match the expected output format: keywords and tone
    train_raw_data = [
        {
            "customer_query": "How do I reset my password?",
            "expected_keywords": "password,reset,login,account,help",
            "expected_tone": "helpful",
            "category": "account_support",
        },
        {
            "customer_query": "What are your pricing plans?",
            "expected_keywords": "pricing,plans,cost,subscription,features",
            "expected_tone": "informative",
            "category": "pricing_inquiry",
        },
        {
            "customer_query": "My app keeps crashing",
            "expected_keywords": "app,crash,technical,support,troubleshoot",
            "expected_tone": "helpful",
            "category": "technical_support",
        },
        {
            "customer_query": "How can I cancel my subscription?",
            "expected_keywords": "cancel,subscription,billing,account,process",
            "expected_tone": "helpful",
            "category": "billing_support",
        },
        {
            "customer_query": "Is there a mobile app available?",
            "expected_keywords": "mobile,app,download,available,platform",
            "expected_tone": "informative",
            "category": "product_inquiry",
        },
    ]

    # Evaluation data - used to test the optimized prompt
    eval_raw_data = [
        {
            "customer_query": "I'm having trouble logging into my account",
            "expected_keywords": "login,account,trouble,access,help",
            "expected_tone": "helpful",
            "category": "account_support",
        },
        {
            "customer_query": "Do you offer student discounts?",
            "expected_keywords": "student,discount,pricing,education,offer",
            "expected_tone": "informative",
            "category": "pricing_inquiry",
        },
        {
            "customer_query": "The website is loading very slowly",
            "expected_keywords": "website,slow,loading,performance,technical",
            "expected_tone": "helpful",
            "category": "technical_support",
        },
    ]

    # Convert to pandas DataFrames for MLflow dataset integration
    train_df = pd.DataFrame(train_raw_data)
    eval_df = pd.DataFrame(eval_raw_data)

    # Log datasets as artifacts for tracking and lineage
    train_csv_path = "training_data.csv"
    eval_csv_path = "evaluation_data.csv"
    train_df.to_csv(train_csv_path, index=False)
    eval_df.to_csv(eval_csv_path, index=False)

    mlflow.log_artifact(train_csv_path, "datasets")
    mlflow.log_artifact(eval_csv_path, "datasets")

    # Clean up temporary files
    import os

    os.remove(train_csv_path)
    os.remove(eval_csv_path)

    # Convert back to the format expected by optimize_prompt
    train_data = []
    for _, row in train_df.iterrows():
        train_data.append(
            {
                "inputs": {"customer_query": str(row["customer_query"])},
                "expectations": {
                    "keywords": str(row["expected_keywords"]).split(","),
                    "tone": str(row["expected_tone"]),
                },
            }
        )

    eval_data = []
    for _, row in eval_df.iterrows():
        eval_data.append(
            {
                "inputs": {"customer_query": str(row["customer_query"])},
                "expectations": {
                    "keywords": str(row["expected_keywords"]).split(","),
                    "tone": str(row["expected_tone"]),
                },
            }
        )

    # Log data statistics
    mlflow.log_metric("training_examples", len(train_data))
    mlflow.log_metric("evaluation_examples", len(eval_data))
    mlflow.log_param("data_categories", list(train_df["category"].unique()))

    return train_data, eval_data


@mlflow.trace
def run_prompt_optimization():
    """
    Main function to demonstrate MLflow prompt optimization with DSPy.
    Enhanced with comprehensive MLflow tracking and experiment management.
    """

    # Set experiment for better organization with robust error handling
    import datetime

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_experiment_name = "Customer_Service_Prompt_Optimization"

    # Try multiple experiment names in case of conflicts
    experiment_names_to_try = [
        f"{base_experiment_name}_v2",
        f"{base_experiment_name}_{timestamp}",
        f"CS_Prompt_Opt_{timestamp}",
        f"Prompt_Optimization_{timestamp}",
    ]

    experiment_name = None
    for name in experiment_names_to_try:
        try:
            mlflow.set_experiment(name)
            experiment_name = name
            break
        except mlflow.exceptions.MlflowException as e:
            print(f"⚠️ Could not set experiment '{name}': {e}")
            continue

    if experiment_name is None:
        # Fallback to default experiment
        print("⚠️ Using default experiment due to conflicts")
        experiment_name = "Default"

    print("🚀 Starting MLflow Prompt Optimization with DSPy...")
    print(f"📊 Experiment: {experiment_name}")

    # Start a comprehensive MLflow run
    with mlflow.start_run(run_name="dspy_prompt_optimization_demo"):
        # Log experiment metadata
        mlflow.log_param("optimization_algorithm", "DSPy_MIPROv2")
        mlflow.log_param("model_provider", "ollama")
        mlflow.log_param("model_name", "qwen3:1.7b")
        mlflow.log_param(
            "optimization_objective",
            "keyword_quality + professionalism - length_penalty",
        )

        # Register the initial prompt
        initial_template = """
        Answer the customer service question professionally and helpfully.
        
        Customer Query: {{customer_query}}
        
        Response:
        """

        print("📝 Registering initial prompt...")
        prompt = mlflow.genai.register_prompt(
            name="customer_service_qa",
            template=initial_template,
        )

        # Log initial prompt details
        mlflow.log_param("initial_prompt_uri", prompt.uri)
        mlflow.log_param("initial_prompt_version", prompt.version)
        mlflow.log_text(initial_template, "initial_prompt_template.txt")

        print(f"✅ Prompt registered with URI: {prompt.uri}")

        # Get training and evaluation data (this will also log datasets)
        train_data, eval_data = setup_optimization_data()

        print(f"📊 Training data: {len(train_data)} examples")
        print(f"📊 Evaluation data: {len(eval_data)} examples")

        # Configure optimization with default settings
        optimizer_config = OptimizerConfig()

        # Log optimization configuration
        mlflow.log_param("num_instruction_candidates", 8)
        mlflow.log_param("max_few_show_examples", 2)
        mlflow.log_param(
            "scorer_functions",
            ["response_quality", "professionalism_check", "length_scorer"],
        )

        # Set up target LLM parameters for Ollama using the correct format
        # MLflow expects format: '<provider>/<model>' or '<provider>:/<model>'
        target_llm_params = LLMParams(model_name="ollama:/qwen3:1.7b")

        print("🔧 Starting prompt optimization...")
        print(
            "⚠️  Note: This requires Ollama running locally with qwen3:1.7b model available"
        )

        try:
            # Run the actual optimization
            result = mlflow.genai.optimize_prompt(
                target_llm_params=target_llm_params,
                prompt=prompt,
                train_data=train_data,
                eval_data=eval_data,
                scorers=[response_quality, professionalism_check, length_scorer],
                optimizer_config=optimizer_config,
                objective=lambda scores: scores["response_quality"]
                + scores["professionalism_check"]
                - scores[
                    "length_scorer"
                ],  # length_scorer returns penalty, so subtract it
            )

            # Log optimization results
            mlflow.log_metric("optimization_initial_score", result.initial_eval_score)
            mlflow.log_metric("optimization_final_score", result.final_eval_score)
            mlflow.log_metric(
                "score_improvement", result.final_eval_score - result.initial_eval_score
            )
            mlflow.log_param("optimized_prompt_uri", result.prompt.uri)
            mlflow.log_param("optimized_prompt_version", result.prompt.version)

            print("✅ Optimization completed successfully!")
            print(f"📈 Initial score: {result.initial_eval_score}")
            print(f"📈 Final score: {result.final_eval_score}")
            print(f"🔗 Optimized prompt URI: {result.prompt.uri}")

            # Load and display the optimized prompt
            optimized_prompt = mlflow.genai.load_prompt(result.prompt.uri)
            print("\n📝 Optimized Prompt Template:")
            print("=" * 50)
            print(optimized_prompt.template)
            print("=" * 50)

            # Log the optimized prompt template
            mlflow.log_text(
                str(optimized_prompt.template), "optimized_prompt_template.txt"
            )

            # Log run as successful
            mlflow.log_param("optimization_status", "success")

            return result

        except Exception as e:
            # Log the error
            mlflow.log_param("optimization_status", "failed")
            mlflow.log_param("error_message", str(e))

            print(f"❌ Optimization failed: {str(e)}")
            print("💡 Make sure you have:")
            print("   1. Ollama running locally (ollama serve)")
            print("   2. qwen3:1.7b model pulled (ollama pull qwen3:1.7b)")
            print(
                "   3. Installed required dependencies: pip install dspy>=2.6.0 mlflow>=3.1.0"
            )

            return None


@mlflow.trace
def demonstrate_optimized_prompt_usage(prompt_uri: str):
    """
    Demonstrate how to use the optimized prompt in an application.
    Enhanced with MLflow tracing for comprehensive monitoring.
    """
    import requests
    import json
    import time

    print("\n🔍 Demonstrating optimized prompt usage...")

    with mlflow.start_run(run_name="prompt_usage_demo", nested=True):
        # Log demo parameters
        mlflow.log_param("prompt_uri", prompt_uri)
        mlflow.log_param("demo_type", "optimized_prompt_usage")

        # Load the optimized prompt
        prompt = mlflow.genai.load_prompt(prompt_uri)
        mlflow.log_param("loaded_prompt_version", prompt.version)

        # Test queries for comprehensive demonstration
        test_queries = [
            "I can't access my account and need help urgently",
            "What are your pricing options for small businesses?",
            "The mobile app crashes when I try to upload photos",
        ]

        results = []

        for i, test_query in enumerate(test_queries):
            print(f"\n🧪 Test {i + 1}: {test_query}")

            # Format the prompt with the test query
            formatted_prompt = prompt.format(customer_query=test_query)

            mlflow.log_param(f"test_query_{i + 1}", test_query)
            mlflow.log_text(str(formatted_prompt), f"formatted_prompt_{i + 1}.txt")

            try:
                # Time the API call
                start_time = time.time()

                # Make API call to local Ollama instance
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "qwen3:1.7b",
                        "prompt": formatted_prompt,
                        "stream": False,
                        "think": False,
                    },
                )

                end_time = time.time()
                response_time = end_time - start_time

                if response.status_code == 200:
                    result = response.json()
                    model_response = result.get("response", "")

                    print(f"🤖 Response: {model_response}")

                    # Try to parse JSON response for structured output
                    try:
                        parsed_response = json.loads(model_response)
                        keywords = parsed_response.get("keywords", [])
                        tone = parsed_response.get("tone", "")

                        # Log parsed response metrics
                        mlflow.log_metric(f"test_{i + 1}_keywords_count", len(keywords))
                        mlflow.log_param(f"test_{i + 1}_detected_tone", tone)
                        mlflow.log_param(f"test_{i + 1}_keywords", str(keywords))

                        results.append(
                            {
                                "query": test_query,
                                "keywords": keywords,
                                "tone": tone,
                                "response_time": response_time,
                                "status": "success",
                            }
                        )

                    except json.JSONDecodeError:
                        print("⚠️ Response is not valid JSON")
                        mlflow.log_param(
                            f"test_{i + 1}_parse_status", "failed_json_parse"
                        )
                        results.append(
                            {
                                "query": test_query,
                                "raw_response": model_response,
                                "response_time": response_time,
                                "status": "non_json_response",
                            }
                        )

                    # Log response metrics
                    mlflow.log_metric(
                        f"test_{i + 1}_response_time_ms", response_time * 1000
                    )
                    mlflow.log_metric(
                        f"test_{i + 1}_response_length", len(model_response)
                    )
                    mlflow.log_text(model_response, f"model_response_{i + 1}.txt")

                else:
                    print(
                        f"❌ API call failed with status code: {response.status_code}"
                    )
                    mlflow.log_param(
                        f"test_{i + 1}_error", f"HTTP_{response.status_code}"
                    )
                    results.append(
                        {
                            "query": test_query,
                            "status": "api_error",
                            "error_code": response.status_code,
                        }
                    )

            except Exception as e:
                error_msg = str(e)
                print(f"❌ API call failed: {error_msg}")
                mlflow.log_param(f"test_{i + 1}_error", error_msg)
                results.append(
                    {"query": test_query, "status": "exception", "error": error_msg}
                )

        # Log overall demo results
        successful_tests = sum(1 for r in results if r.get("status") == "success")
        mlflow.log_metric("total_tests", len(test_queries))
        mlflow.log_metric("successful_tests", successful_tests)
        mlflow.log_metric("success_rate", successful_tests / len(test_queries))

        if successful_tests > 0:
            avg_response_time = (
                sum(r.get("response_time", 0) for r in results if "response_time" in r)
                / successful_tests
            )
            mlflow.log_metric("average_response_time_ms", avg_response_time * 1000)

        # Log results summary
        results_dict = {"test_results": results}
        mlflow.log_dict(results_dict, "demo_results.json")

        print(
            f"\n📊 Demo Summary: {successful_tests}/{len(test_queries)} tests successful"
        )

        if successful_tests == 0:
            print("💡 Make sure Ollama is running locally with qwen3:1.7b model")

        return results


if __name__ == "__main__":
    # Run the optimization
    result = run_prompt_optimization()

    if result:
        # Demonstrate usage of the optimized prompt
        demonstrate_optimized_prompt_usage(result.prompt.uri)
    else:
        print("\n📚 To run this example, you need:")
        print("   1. ollama serve (start Ollama service)")
        print("   2. ollama pull qwen3:1.7b (download the model)")
        print("   3. pip install dspy>=2.6.0 mlflow>=3.1.0 requests")
        print("   4. Run: python dspy_optimization.py")
