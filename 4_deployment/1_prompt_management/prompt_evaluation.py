#!/usr/bin/env python3
import mlflow
import requests
import time
from datetime import datetime

# Configure MLflow
mlflow.set_tracking_uri("http://127.0.0.1:8080")


def evaluate_prompt_performance(prompt_template, test_cases, model="qwen3:1.7b"):
    """Evaluate a prompt template against test cases"""

    results = []
    total_time = 0

    for i, test_case in enumerate(test_cases):
        # Format the prompt with test data
        formatted_prompt = prompt_template.format(**test_case["inputs"])

        start_time = time.time()

        try:
            # Make request to local model
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": formatted_prompt,
                    "stream": False,
                    "think": False,
                },
            )

            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # Convert to ms
            total_time += response_time

            data = response.json()
            llm_response = data["response"]

            # Simple quality scoring (in production, use more sophisticated metrics)
            quality_score = min(
                1.0, len(llm_response.strip()) / 100
            )  # Basic length-based score
            relevance_score = (
                1.0
                if any(
                    keyword in llm_response.lower()
                    for keyword in test_case.get("expected_keywords", [])
                )
                else 0.5
            )

            result = {
                "test_case_id": i,
                "response_time_ms": response_time,
                "response_length": len(llm_response),
                "quality_score": quality_score,
                "relevance_score": relevance_score,
                "response": llm_response[:200] + "..."
                if len(llm_response) > 200
                else llm_response,
            }

            results.append(result)

        except Exception as e:
            results.append(
                {
                    "test_case_id": i,
                    "error": str(e),
                    "response_time_ms": (time.time() - start_time) * 1000,
                }
            )

    # Calculate aggregate metrics
    successful_results = [r for r in results if "error" not in r]

    if successful_results:
        avg_response_time = sum(
            r["response_time_ms"] for r in successful_results
        ) / len(successful_results)
        avg_quality = sum(r["quality_score"] for r in successful_results) / len(
            successful_results
        )
        avg_relevance = sum(r["relevance_score"] for r in successful_results) / len(
            successful_results
        )
        success_rate = len(successful_results) / len(results)

        return {
            "avg_response_time_ms": avg_response_time,
            "avg_quality_score": avg_quality,
            "avg_relevance_score": avg_relevance,
            "success_rate": success_rate,
            "total_tests": len(results),
            "successful_tests": len(successful_results),
            "detailed_results": results,
        }

    return {"error": "No successful evaluations"}


def run_ab_test():
    """Compare two prompt versions with A/B testing"""

    # Define test cases
    test_cases = [
        {
            "inputs": {"customer_query": "How do I reset my password?"},
            "expected_keywords": ["password", "reset", "email", "account"],
        },
        {
            "inputs": {"customer_query": "What are your pricing plans?"},
            "expected_keywords": ["pricing", "plan", "cost", "subscription"],
        },
        {
            "inputs": {"customer_query": "My app is crashing on iOS"},
            "expected_keywords": ["ios", "crash", "bug", "update", "support"],
        },
        {
            "inputs": {"customer_query": "Can I export my data?"},
            "expected_keywords": ["export", "data", "download", "csv", "excel"],
        },
    ]

    # Version A: Simple prompt
    prompt_a = """You are a customer service assistant.

Customer question: {customer_query}

Please provide a helpful response."""

    # Version B: Structured prompt
    prompt_b = """You are a professional customer service representative for TechCorp.

Customer Question: {customer_query}

Response Guidelines:
1. Address the customer's specific question
2. Provide clear, actionable steps when possible
3. Be empathetic and professional
4. Offer additional help if needed

Response:"""

    print("🔄 Running A/B Test Evaluation...")

    # Evaluate both versions
    results_a = evaluate_prompt_performance(prompt_a, test_cases)
    results_b = evaluate_prompt_performance(prompt_b, test_cases)

    # Log results to MLflow
    with mlflow.start_run(run_name="ab_test_comparison"):
        mlflow.log_param("test_type", "ab_test")
        mlflow.log_param("test_cases_count", len(test_cases))
        mlflow.log_param("evaluation_date", datetime.now().isoformat())

        # Log Version A metrics
        if "error" not in results_a:
            mlflow.log_metric(
                "version_a_avg_response_time", results_a["avg_response_time_ms"]
            )
            mlflow.log_metric("version_a_avg_quality", results_a["avg_quality_score"])
            mlflow.log_metric(
                "version_a_avg_relevance", results_a["avg_relevance_score"]
            )
            mlflow.log_metric("version_a_success_rate", results_a["success_rate"])

        # Log Version B metrics
        if "error" not in results_b:
            mlflow.log_metric(
                "version_b_avg_response_time", results_b["avg_response_time_ms"]
            )
            mlflow.log_metric("version_b_avg_quality", results_b["avg_quality_score"])
            mlflow.log_metric(
                "version_b_avg_relevance", results_b["avg_relevance_score"]
            )
            mlflow.log_metric("version_b_success_rate", results_b["success_rate"])

        # Determine winner
        if "error" not in results_a and "error" not in results_b:
            # Simple scoring: quality + relevance - normalized_response_time
            score_a = (
                results_a["avg_quality_score"]
                + results_a["avg_relevance_score"]
                - (results_a["avg_response_time_ms"] / 10000)
            )
            score_b = (
                results_b["avg_quality_score"]
                + results_b["avg_relevance_score"]
                - (results_b["avg_response_time_ms"] / 10000)
            )

            winner = "B" if score_b > score_a else "A"
            confidence = abs(score_b - score_a) / max(score_a, score_b)

            mlflow.log_param("winner", f"Version_{winner}")
            mlflow.log_metric("confidence_level", confidence)

            print("\n📊 A/B Test Results:")
            print(f"Version A Score: {score_a:.3f}")
            print(f"Version B Score: {score_b:.3f}")
            print(f"🏆 Winner: Version {winner} (confidence: {confidence:.2%})")

            if confidence > 0.1:
                print("✅ Statistically significant difference detected")
                mlflow.log_param("recommendation", f"Deploy Version {winner}")
            else:
                print("⚠️  Difference not significant, continue testing")
                mlflow.log_param("recommendation", "Continue testing")


if __name__ == "__main__":
    run_ab_test()
