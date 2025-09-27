#!/usr/bin/env python3
"""
Debug Agent - Comprehensive debugging and observability patterns
"""
import json
import time
import traceback
from typing import Dict
from datetime import datetime

class AgentDebugger:
    def __init__(self, log_level: str = "INFO"):
        self.log_level = log_level
        self.execution_trace = []
        self.performance_metrics = {}
        self.error_log = []

        self.log_levels = {"DEBUG": 0, "INFO": 1, "WARN": 2, "ERROR": 3}

    def log(self, level: str, message: str, context: Dict = None):
        """Structured logging with context"""
        if self.log_levels[level] >= self.log_levels[self.log_level]:
            timestamp = datetime.now().isoformat()

            # Color coding for terminal output
            colors = {
                "DEBUG": "\033[94m",  # Blue
                "INFO": "\033[92m",   # Green
                "WARN": "\033[93m",   # Yellow
                "ERROR": "\033[91m"   # Red
            }
            reset_color = "\033[0m"

            color = colors.get(level, "")
            print(f"{color}[{level}] {timestamp[:19]} - {message}{reset_color}")

            if context:
                print(f"  Context: {json.dumps(context, indent=2)}")

    def start_trace(self, operation: str):
        """Start tracing an operation"""
        trace_id = f"trace_{int(time.time() * 1000)}"
        trace_entry = {
            "trace_id": trace_id,
            "operation": operation,
            "start_time": time.time(),
            "steps": [],
            "status": "running"
        }
        self.execution_trace.append(trace_entry)
        self.log("DEBUG", f"Started trace: {operation}", {"trace_id": trace_id})
        return trace_id

    def add_trace_step(self, trace_id: str, step: str, details: Dict = None):
        """Add a step to the execution trace"""
        for trace in self.execution_trace:
            if trace["trace_id"] == trace_id:
                step_entry = {
                    "step": step,
                    "timestamp": time.time(),
                    "details": details or {}
                }
                trace["steps"].append(step_entry)
                self.log("DEBUG", f"Trace step: {step}", {"trace_id": trace_id})
                break

    def end_trace(self, trace_id: str, status: str = "completed"):
        """End a trace and calculate metrics"""
        for trace in self.execution_trace:
            if trace["trace_id"] == trace_id:
                trace["end_time"] = time.time()
                trace["duration"] = trace["end_time"] - trace["start_time"]
                trace["status"] = status
                self.log("INFO", f"Trace completed: {trace['operation']} ({trace['duration']:.3f}s)",
                        {"trace_id": trace_id, "status": status})
                break

    def log_error(self, error: Exception, context: Dict = None):
        """Log errors with full context"""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        self.error_log.append(error_entry)
        self.log("ERROR", f"{type(error).__name__}: {error}", context)

class DebugAgent:
    def __init__(self):
        self.debugger = AgentDebugger(log_level="DEBUG")
        self.call_count = 0

    def mock_llm_call(self, prompt: str, model: str = "qwen3:1.7b") -> Dict:
        """Mock LLM call with debugging"""
        self.call_count += 1
        call_id = f"llm_call_{self.call_count}"

        self.debugger.log("INFO", "LLM call started", {
            "call_id": call_id,
            "model": model,
            "prompt_length": len(prompt)
        })

        # Simulate processing time
        processing_time = 0.5 + (len(prompt) / 1000)
        time.sleep(min(processing_time, 2))  # Cap at 2s for demo

        # Simulate occasional errors
        if self.call_count % 7 == 0:  # Every 7th call fails
            error = Exception("Simulated API timeout")
            self.debugger.log_error(error, {"call_id": call_id})
            raise error

        response = f"Response to: {prompt[:50]}..." if len(prompt) > 50 else f"Response to: {prompt}"

        self.debugger.log("INFO", "LLM call completed", {
            "call_id": call_id,
            "response_length": len(response),
            "processing_time": processing_time
        })

        return {
            "response": response,
            "model": model,
            "call_id": call_id
        }

    def mock_tool_call(self, tool_name: str, args: Dict) -> Dict:
        """Mock tool call with debugging"""
        tool_trace = self.debugger.start_trace(f"tool_call_{tool_name}")

        try:
            self.debugger.add_trace_step(tool_trace, "validate_args", {"args": args})

            # Simulate validation
            if not args:
                raise ValueError("Tool arguments cannot be empty")

            self.debugger.add_trace_step(tool_trace, "execute_tool", {"tool": tool_name})

            # Simulate tool execution
            time.sleep(0.3)

            result = f"Tool {tool_name} executed with args {args}"

            self.debugger.add_trace_step(tool_trace, "process_result", {"result_length": len(result)})
            self.debugger.end_trace(tool_trace, "success")

            return {"result": result, "tool": tool_name}

        except Exception as e:
            self.debugger.log_error(e, {"tool_name": tool_name, "args": args})
            self.debugger.end_trace(tool_trace, "failed")
            raise

    def debug_agent_execution(self, task: str):
        """Execute task with comprehensive debugging"""
        execution_trace = self.debugger.start_trace("agent_execution")

        self.debugger.log("INFO", "Starting agent execution", {"task": task})

        try:
            # Step 1: Planning
            self.debugger.add_trace_step(execution_trace, "planning_phase")
            self.debugger.log("DEBUG", "Agent planning phase", {"task": task})

            plan_prompt = f"Create a plan for: {task}"
            self.mock_llm_call(plan_prompt)

            # Step 2: Research
            self.debugger.add_trace_step(execution_trace, "research_phase")
            self.debugger.log("DEBUG", "Agent research phase")

            research_result = self.mock_tool_call("search_tool", {"query": task})

            # Step 3: Analysis
            self.debugger.add_trace_step(execution_trace, "analysis_phase")
            self.debugger.log("DEBUG", "Agent analysis phase")

            analysis_prompt = f"Analyze the research for {task}: {research_result['result']}"
            self.mock_llm_call(analysis_prompt)

            # Step 4: Synthesis
            self.debugger.add_trace_step(execution_trace, "synthesis_phase")
            self.debugger.log("DEBUG", "Agent synthesis phase")

            synthesis_prompt = f"Synthesize findings for {task}"
            final_result = self.mock_llm_call(synthesis_prompt)

            self.debugger.end_trace(execution_trace, "completed")
            self.debugger.log("INFO", "Agent execution completed successfully")

            return {
                "success": True,
                "result": final_result["response"],
                "trace_id": execution_trace
            }

        except Exception as e:
            self.debugger.log_error(e, {"task": task})
            self.debugger.end_trace(execution_trace, "failed")
            return {
                "success": False,
                "error": str(e),
                "trace_id": execution_trace
            }

    def generate_debug_report(self):
        """Generate comprehensive debug report"""
        print("\n🔍 Debug Report")
        print("=" * 40)

        # Execution traces summary
        print("\n📊 Execution Summary:")
        print(f"Total traces: {len(self.debugger.execution_trace)}")
        print(f"Total errors: {len(self.debugger.error_log)}")
        print(f"LLM calls made: {self.call_count}")

        # Performance metrics
        if self.debugger.execution_trace:
            avg_duration = sum(t.get("duration", 0) for t in self.debugger.execution_trace) / len(self.debugger.execution_trace)
            print(f"Average trace duration: {avg_duration:.3f}s")

        # Recent traces
        print("\n📋 Recent Traces:")
        for trace in self.debugger.execution_trace[-3:]:
            status_emoji = "✅" if trace["status"] == "completed" else "❌"
            print(f"  {status_emoji} {trace['operation']}: {trace.get('duration', 0):.3f}s ({len(trace['steps'])} steps)")

        # Error summary
        if self.debugger.error_log:
            print("\n❌ Error Summary:")
            error_types = {}
            for error in self.debugger.error_log:
                error_type = error["error_type"]
                error_types[error_type] = error_types.get(error_type, 0) + 1

            for error_type, count in error_types.items():
                print(f"  • {error_type}: {count} occurrences")

        # Debug recommendations
        print("\n💡 Debug Insights:")
        if len(self.debugger.error_log) > 0:
            print("- High error rate detected, review error handling")
        if self.call_count > 10:
            print("- Many LLM calls made, consider caching or optimization")
        print("- Use trace IDs to correlate logs across distributed systems")
        print("- Monitor performance trends over time")

def main():
    print("🐛 Agent Debugging Demonstration")
    print("=" * 50)

    agent = DebugAgent()

    # Test tasks with different complexity
    test_tasks = [
        "Simple data analysis task",
        "Complex multi-step research project",
        "Error-prone processing task"
    ]

    for i, task in enumerate(test_tasks, 1):
        print(f"\n🧪 Test {i}: {task}")
        print("-" * 30)

        result = agent.debug_agent_execution(task)

        if result["success"]:
            print(f"✅ Task completed: {result['result'][:50]}...")
        else:
            print(f"❌ Task failed: {result['error']}")

        time.sleep(0.5)

    # Generate final debug report
    agent.generate_debug_report()

    print("\n🔧 Debugging Best Practices:")
    print("1. Use structured logging with context")
    print("2. Implement distributed tracing")
    print("3. Capture performance metrics")
    print("4. Log all errors with full context")
    print("5. Create actionable debug reports")
    print("6. Monitor trends and patterns")

if __name__ == "__main__":
    main()