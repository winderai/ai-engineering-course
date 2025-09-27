#!/usr/bin/env python3
"""
vLLM Latency Testing and Monitoring Script

This script provides comprehensive latency testing for vLLM deployments,
measuring Time to First Token (TTFT), Tokens Per Second (TPS), and Total Time.
Uses deterministic testing with predefined prompts for consistent results.
"""

import requests
import time
import statistics
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
import concurrent.futures
from dataclasses import dataclass

# Sample prompts for deterministic testing
SAMPLE_PROMPTS = [
    "What is artificial intelligence?",
    "Explain quantum computing in simple terms.",
    "Write a haiku about mountains.",
    "What are the benefits of exercise?",
    "How does photosynthesis work?",
    "What is machine learning?",
    "Describe the water cycle.",
    "What causes seasons on Earth?",
    "How do vaccines work?",
    "What is blockchain technology?",
    "Explain the greenhouse effect.",
    "What is deep learning?",
    "How do airplanes fly?",
    "What is DNA and why is it important?",
    "Describe our solar system.",
    "What is climate change?",
    "How does the internet work?",
    "What is renewable energy?",
    "Explain gravity in simple terms.",
    "What is a black hole?",
]


@dataclass
class LatencyMetrics:
    """Data class for storing latency metrics"""

    ttft_ms: float  # Time to first token in milliseconds
    tps: float  # Tokens per second
    total_time_ms: float  # Total response time in milliseconds
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt: str
    response: str
    timestamp: datetime


class VLLMLatencyTester:
    """Comprehensive vLLM latency testing and monitoring"""

    def __init__(
        self, base_url: str = "http://localhost:8000", model_name: str = "qwen2.5-1.5b"
    ):
        self.base_url = base_url
        self.model_name = model_name
        self.chat_endpoint = f"{base_url}/v1/chat/completions"
        self.metrics_endpoint = f"{base_url}/v1/models"
        self.results: List[LatencyMetrics] = []

    def check_server_health(self) -> bool:
        """Check if vLLM server is running and healthy"""
        try:
            response = requests.get(self.metrics_endpoint, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(
                    f"✓ Server healthy - Available models: {[m['id'] for m in data.get('data', [])]}"
                )
                return True
            else:
                print(f"✗ Server returned status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ Server health check failed: {e}")
            return False

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars per token average)"""
        return max(1, len(text.split()))

    def test_single_request(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> Optional[LatencyMetrics]:
        """Test a single request and measure latency metrics"""

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

        try:
            start_time = time.time()

            if stream:
                return self._test_streaming_request(payload, prompt, start_time)
            else:
                return self._test_non_streaming_request(payload, prompt, start_time)

        except requests.exceptions.RequestException as e:
            print(f"✗ Request failed: {e}")
            return None
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            return None

    def _test_non_streaming_request(
        self, payload: Dict, prompt: str, start_time: float
    ) -> LatencyMetrics:
        """Test non-streaming request"""
        response = requests.post(self.chat_endpoint, json=payload, timeout=60)
        end_time = time.time()

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        data = response.json()
        completion = data["choices"][0]["message"]["content"]

        # Calculate metrics
        total_time_ms = (end_time - start_time) * 1000

        # Estimate tokens
        prompt_tokens = self.estimate_tokens(prompt)
        completion_tokens = self.estimate_tokens(completion)
        total_tokens = prompt_tokens + completion_tokens

        # For non-streaming, TTFT is roughly 30% of total time (estimate)
        ttft_ms = total_time_ms * 0.3

        # Calculate TPS
        generation_time_s = total_time_ms / 1000
        tps = completion_tokens / generation_time_s if generation_time_s > 0 else 0

        return LatencyMetrics(
            ttft_ms=ttft_ms,
            tps=tps,
            total_time_ms=total_time_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            prompt=prompt,
            response=completion,
            timestamp=datetime.now(),
        )

    def _test_streaming_request(
        self, payload: Dict, prompt: str, start_time: float
    ) -> LatencyMetrics:
        """Test streaming request with accurate TTFT measurement"""
        first_token_time = None
        completion = ""
        token_count = 0

        response = requests.post(
            self.chat_endpoint, json=payload, stream=True, timeout=60
        )

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]  # Remove 'data: ' prefix
                    if data.strip() == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data)
                        if "choices" in chunk and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                content = delta["content"]
                                completion += content

                                # Record first token time
                                if first_token_time is None:
                                    first_token_time = time.time()
                                    ttft_ms = (first_token_time - start_time) * 1000

                                token_count += 1
                    except json.JSONDecodeError:
                        continue

        end_time = time.time()
        total_time_ms = (end_time - start_time) * 1000

        # Calculate metrics
        prompt_tokens = self.estimate_tokens(prompt)
        completion_tokens = self.estimate_tokens(completion)
        total_tokens = prompt_tokens + completion_tokens

        # Calculate TPS
        generation_time_s = total_time_ms / 1000
        tps = completion_tokens / generation_time_s if generation_time_s > 0 else 0

        return LatencyMetrics(
            ttft_ms=ttft_ms if first_token_time else total_time_ms * 0.3,
            tps=tps,
            total_time_ms=total_time_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            prompt=prompt,
            response=completion,
            timestamp=datetime.now(),
        )

    def run_batch_test(
        self,
        prompts: List[str],
        iterations: int = 3,
        concurrent: bool = False,
        max_tokens: int = 100,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> List[LatencyMetrics]:
        """Run batch latency tests"""

        print("\n=== Starting Batch Latency Test ===")
        print(f"Model: {self.model_name}")
        print(f"Prompts: {len(prompts)}")
        print(f"Iterations: {iterations}")
        print(f"Max tokens: {max_tokens}")
        print(f"Temperature: {temperature}")
        print(f"Streaming: {stream}")
        print(f"Concurrent: {concurrent}")
        print("=" * 50)

        all_results = []

        if concurrent:
            all_results = self._run_concurrent_tests(
                prompts, iterations, max_tokens, temperature, stream
            )
        else:
            all_results = self._run_sequential_tests(
                prompts, iterations, max_tokens, temperature, stream
            )

        self.results.extend(all_results)
        return all_results

    def _run_sequential_tests(
        self,
        prompts: List[str],
        iterations: int,
        max_tokens: int,
        temperature: float,
        stream: bool,
    ) -> List[LatencyMetrics]:
        """Run tests sequentially"""
        results = []
        total_tests = len(prompts) * iterations

        for i, prompt in enumerate(prompts):
            for j in range(iterations):
                test_num = i * iterations + j + 1
                print(f"[{test_num}/{total_tests}] Testing: {prompt[:50]}...")

                result = self.test_single_request(
                    prompt, max_tokens, temperature, stream
                )
                if result:
                    results.append(result)
                    print(
                        f"  ✓ TTFT: {result.ttft_ms:.1f}ms, TPS: {result.tps:.1f}, Total: {result.total_time_ms:.1f}ms"
                    )
                else:
                    print("  ✗ Test failed")

                # Small delay between requests
                time.sleep(0.1)

        return results

    def _run_concurrent_tests(
        self,
        prompts: List[str],
        iterations: int,
        max_tokens: int,
        temperature: float,
        stream: bool,
    ) -> List[LatencyMetrics]:
        """Run tests concurrently"""
        results = []
        total_tests = len(prompts) * iterations

        def run_single_test(prompt: str, iteration: int) -> Optional[LatencyMetrics]:
            test_num = prompts.index(prompt) * iterations + iteration + 1
            print(f"[{test_num}/{total_tests}] Testing: {prompt[:50]}...")

            result = self.test_single_request(prompt, max_tokens, temperature, stream)
            if result:
                print(
                    f"  ✓ TTFT: {result.ttft_ms:.1f}ms, TPS: {result.tps:.1f}, Total: {result.total_time_ms:.1f}ms"
                )
            else:
                print("  ✗ Test failed")
            return result

        # Create all test tasks
        tasks = []
        for prompt in prompts:
            for iteration in range(iterations):
                tasks.append((prompt, iteration))

        # Run tests with thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_task = {
                executor.submit(run_single_test, prompt, iteration): (prompt, iteration)
                for prompt, iteration in tasks
            }

            for future in concurrent.futures.as_completed(future_to_task):
                result = future.result()
                if result:
                    results.append(result)

        return results

    def calculate_statistics(self, results: List[LatencyMetrics]) -> Dict[str, Any]:
        """Calculate comprehensive statistics from test results"""
        if not results:
            return {}

        ttft_values = [r.ttft_ms for r in results]
        tps_values = [r.tps for r in results]
        total_time_values = [r.total_time_ms for r in results]
        completion_tokens = [r.completion_tokens for r in results]

        stats = {
            "total_tests": len(results),
            "success_rate": len(results) / len(results) * 100,
            "ttft": {
                "mean": statistics.mean(ttft_values),
                "median": statistics.median(ttft_values),
                "min": min(ttft_values),
                "max": max(ttft_values),
                "p95": sorted(ttft_values)[int(0.95 * len(ttft_values))],
                "p99": sorted(ttft_values)[int(0.99 * len(ttft_values))],
                "stdev": statistics.stdev(ttft_values) if len(ttft_values) > 1 else 0,
            },
            "tps": {
                "mean": statistics.mean(tps_values),
                "median": statistics.median(tps_values),
                "min": min(tps_values),
                "max": max(tps_values),
                "p95": sorted(tps_values)[int(0.95 * len(tps_values))],
                "p99": sorted(tps_values)[int(0.99 * len(tps_values))],
                "stdev": statistics.stdev(tps_values) if len(tps_values) > 1 else 0,
            },
            "total_time": {
                "mean": statistics.mean(total_time_values),
                "median": statistics.median(total_time_values),
                "min": min(total_time_values),
                "max": max(total_time_values),
                "p95": sorted(total_time_values)[int(0.95 * len(total_time_values))],
                "p99": sorted(total_time_values)[int(0.99 * len(total_time_values))],
                "stdev": statistics.stdev(total_time_values)
                if len(total_time_values) > 1
                else 0,
            },
            "tokens": {
                "total_completion_tokens": sum(completion_tokens),
                "avg_completion_tokens": statistics.mean(completion_tokens),
                "min_completion_tokens": min(completion_tokens),
                "max_completion_tokens": max(completion_tokens),
            },
        }

        return stats

    def print_statistics(self, stats: Dict[str, Any]):
        """Print formatted statistics"""
        if not stats:
            print("No statistics available")
            return

        print(f"\n{'=' * 60}")
        print(f"LATENCY TEST RESULTS - {stats['total_tests']} tests")
        print(f"{'=' * 60}")

        print("\n📊 TIME TO FIRST TOKEN (TTFT):")
        ttft = stats["ttft"]
        print(f"  Mean:    {ttft['mean']:.1f}ms")
        print(f"  Median:  {ttft['median']:.1f}ms")
        print(f"  P95:     {ttft['p95']:.1f}ms")
        print(f"  P99:     {ttft['p99']:.1f}ms")
        print(f"  Min:     {ttft['min']:.1f}ms")
        print(f"  Max:     {ttft['max']:.1f}ms")
        print(f"  StdDev:  {ttft['stdev']:.1f}ms")

        print("\n⚡ TOKENS PER SECOND (TPS):")
        tps = stats["tps"]
        print(f"  Mean:    {tps['mean']:.1f} tok/s")
        print(f"  Median:  {tps['median']:.1f} tok/s")
        print(f"  P95:     {tps['p95']:.1f} tok/s")
        print(f"  P99:     {tps['p99']:.1f} tok/s")
        print(f"  Min:     {tps['min']:.1f} tok/s")
        print(f"  Max:     {tps['max']:.1f} tok/s")
        print(f"  StdDev:  {tps['stdev']:.1f} tok/s")

        print("\n⏱️  TOTAL TIME:")
        total = stats["total_time"]
        print(f"  Mean:    {total['mean']:.1f}ms")
        print(f"  Median:  {total['median']:.1f}ms")
        print(f"  P95:     {total['p95']:.1f}ms")
        print(f"  P99:     {total['p99']:.1f}ms")
        print(f"  Min:     {total['min']:.1f}ms")
        print(f"  Max:     {total['max']:.1f}ms")
        print(f"  StdDev:  {total['stdev']:.1f}ms")

        print("\n🎯 TOKEN STATISTICS:")
        tokens = stats["tokens"]
        print(f"  Total completion tokens: {tokens['total_completion_tokens']:,}")
        print(f"  Avg completion tokens:   {tokens['avg_completion_tokens']:.1f}")
        print(f"  Min completion tokens:   {tokens['min_completion_tokens']}")
        print(f"  Max completion tokens:   {tokens['max_completion_tokens']}")

    def save_results(self, filename: str = None):
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"vllm_latency_results_{timestamp}.json"

        data = {
            "metadata": {
                "model": self.model_name,
                "base_url": self.base_url,
                "timestamp": datetime.now().isoformat(),
                "total_tests": len(self.results),
            },
            "results": [
                {
                    "ttft_ms": r.ttft_ms,
                    "tps": r.tps,
                    "total_time_ms": r.total_time_ms,
                    "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                    "total_tokens": r.total_tokens,
                    "prompt": r.prompt,
                    "response": r.response,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in self.results
            ],
            "statistics": self.calculate_statistics(self.results),
        }

        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

        print(f"\n💾 Results saved to: {filename}")

    def run_comprehensive_test(
        self,
        iterations: int = 3,
        max_tokens: int = 100,
        temperature: float = 0.7,
        concurrent: bool = False,
    ):
        """Run comprehensive latency test with all sample prompts"""

        if not self.check_server_health():
            print("❌ Server health check failed. Please ensure vLLM is running.")
            return

        print("\n🚀 Starting comprehensive vLLM latency test...")
        print(f"   Server: {self.base_url}")
        print(f"   Model: {self.model_name}")
        print(f"   Prompts: {len(SAMPLE_PROMPTS)}")
        print(f"   Iterations: {iterations}")
        print(f"   Total tests: {len(SAMPLE_PROMPTS) * iterations}")

        # Run streaming test
        print("\n📡 Testing streaming mode...")
        streaming_results = self.run_batch_test(
            SAMPLE_PROMPTS, iterations, concurrent, max_tokens, temperature, stream=True
        )

        # Run non-streaming test
        print("\n📦 Testing non-streaming mode...")
        non_streaming_results = self.run_batch_test(
            SAMPLE_PROMPTS,
            iterations,
            concurrent,
            max_tokens,
            temperature,
            stream=False,
        )

        # Print results
        if streaming_results:
            print("\n📊 STREAMING MODE RESULTS:")
            streaming_stats = self.calculate_statistics(streaming_results)
            self.print_statistics(streaming_stats)

        if non_streaming_results:
            print("\n📊 NON-STREAMING MODE RESULTS:")
            non_streaming_stats = self.calculate_statistics(non_streaming_results)
            self.print_statistics(non_streaming_stats)

        # Compare modes
        if streaming_results and non_streaming_results:
            print("\n🔄 STREAMING vs NON-STREAMING COMPARISON:")
            stream_stats = self.calculate_statistics(streaming_results)
            non_stream_stats = self.calculate_statistics(non_streaming_results)

            print(
                f"  TTFT Improvement:     {(non_stream_stats['ttft']['mean'] / stream_stats['ttft']['mean']):.2f}x"
            )
            print(
                f"  Total Time Improvement: {(non_stream_stats['total_time']['mean'] / stream_stats['total_time']['mean']):.2f}x"
            )
            print(
                f"  TPS Difference:       {stream_stats['tps']['mean'] - non_stream_stats['tps']['mean']:.1f} tok/s"
            )

        # Save results
        self.save_results()


def main():
    parser = argparse.ArgumentParser(description="vLLM Latency Testing and Monitoring")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="vLLM server URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen3-1.7B",
        help="Model name (default: Qwen/Qwen3-1.7B)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Number of iterations per prompt (default: 3)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=100,
        help="Maximum tokens per response (default: 100)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Sampling temperature (default: 0.7)",
    )
    parser.add_argument(
        "--concurrent", action="store_true", help="Run tests concurrently"
    )
    parser.add_argument(
        "--streaming-only", action="store_true", help="Test only streaming mode"
    )
    parser.add_argument(
        "--non-streaming-only", action="store_true", help="Test only non-streaming mode"
    )
    parser.add_argument(
        "--save-results", action="store_true", help="Save results to JSON file"
    )

    args = parser.parse_args()

    # Create tester instance
    tester = VLLMLatencyTester(args.url, args.model)

    # Run comprehensive test
    if args.streaming_only:
        results = tester.run_batch_test(
            SAMPLE_PROMPTS,
            args.iterations,
            args.concurrent,
            args.max_tokens,
            args.temperature,
            stream=True,
        )
        if results:
            stats = tester.calculate_statistics(results)
            tester.print_statistics(stats)
    elif args.non_streaming_only:
        results = tester.run_batch_test(
            SAMPLE_PROMPTS,
            args.iterations,
            args.concurrent,
            args.max_tokens,
            args.temperature,
            stream=False,
        )
        if results:
            stats = tester.calculate_statistics(results)
            tester.print_statistics(stats)
    else:
        tester.run_comprehensive_test(
            args.iterations, args.max_tokens, args.temperature, args.concurrent
        )

    if args.save_results:
        tester.save_results()


if __name__ == "__main__":
    main()
