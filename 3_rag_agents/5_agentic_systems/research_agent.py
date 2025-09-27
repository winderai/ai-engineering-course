#!/usr/bin/env python3
"""
Practical research agent using Qwen's native tool calling
"""
import json
import subprocess
import sys

def call_qwen_api(messages, tools=None):
    """Call Qwen via API with tool support"""
    payload = {
        "model": "qwen3:1.7b",
        "messages": messages,
        "stream": False
    }
    if tools:
        payload["tools"] = tools

    try:
        result = subprocess.run([
            'curl', '-s', 'http://localhost:11434/api/chat',
            '-H', 'Content-Type: application/json',
            '-d', json.dumps(payload)
        ], capture_output=True, text=True)

        if result.stdout:
            response = json.loads(result.stdout)
            return response.get('message', {})
        return {"content": "No response from API"}
    except Exception as e:
        return {"content": f"API Error: {e}"}

class ResearchAgent:
    def __init__(self):
        self.findings = []
        self.max_research_rounds = 3
        self.conversation = []

        self.tool_functions = {
            "search_topic": self.search_topic,
            "analyze_findings": self.analyze_findings_tool,
            "create_summary": self.create_summary_tool
        }

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_topic",
                    "description": "Search for information on a specific topic or query",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query or topic to research"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_findings",
                    "description": "Analyze research findings to identify patterns and insights",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "findings": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of research findings to analyze"
                            },
                            "topic": {
                                "type": "string",
                                "description": "The main topic being researched"
                            }
                        },
                        "required": ["findings", "topic"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_summary",
                    "description": "Create a professional research summary",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "The research topic"
                            },
                            "analysis": {
                                "type": "string",
                                "description": "The analysis of findings"
                            }
                        },
                        "required": ["topic", "analysis"]
                    }
                }
            }
        ]

    def search_topic(self, query):
        """Mock research search - in real implementation, use actual APIs"""
        mock_results = {
            "ai agents": "Recent developments include multi-agent systems, ReAct patterns, and tool-augmented LLMs. Key players: OpenAI, Anthropic, Google.",
            "machine learning": "Focus on large language models, reinforcement learning, and MLOps. Major conferences: NeurIPS, ICML, ICLR.",
            "software engineering": "Trends include cloud-native development, microservices, DevOps automation, and AI-assisted coding."
        }

        # Simple keyword matching for demo
        for key, value in mock_results.items():
            if key.lower() in query.lower():
                return value

        return f"General research results for '{query}': Multiple academic papers and industry reports found."

    def analyze_findings_tool(self, findings, topic):
        """Tool wrapper for analysis - returns structured analysis"""
        findings_text = "\n".join(f"- {finding}" for finding in findings)
        return f"""Analysis of {topic}:

Key themes: Multi-modal capabilities, tool integration, reasoning improvements
Important developments: Better tool calling, improved reasoning chains, cost optimizations
Future directions: More specialized agents, better human-AI collaboration
Practical implications: Easier to build reliable AI applications, reduced development time

Based on findings:
{findings_text}"""

    def create_summary_tool(self, topic, analysis):
        """Tool wrapper for summary creation"""
        return f"""# Research Summary: {topic}

## Executive Summary
Current research shows rapid advancement in agentic AI systems with focus on reliability and practical applications. Key developments include improved reasoning capabilities and better tool integration.

## Key Findings
• Enhanced tool calling capabilities in latest models
• Growing adoption of ReAct and similar patterns
• Improved error handling and self-correction
• Better integration with existing software systems
• Focus on cost-effective deployment strategies

## Implications
For practitioners, these developments mean more reliable AI applications, reduced development complexity, and better user experiences. Organizations can now build more sophisticated automation with fewer resources.

## Recommended Reading
• "ReAct: Synergizing Reasoning and Acting in Language Models" - Yao et al.
• "Tool Learning with Foundation Models" - Qin et al.
• "LangChain Documentation" - https://langchain.com/

Analysis based on: {analysis}"""

    def execute_tool_call(self, tool_call):
        """Execute a tool call and return the result"""
        function_name = tool_call.get('function', {}).get('name')
        arguments = json.loads(tool_call.get('function', {}).get('arguments', '{}'))

        if function_name in self.tool_functions:
            result = self.tool_functions[function_name](**arguments)
            if function_name == "search_topic":
                self.findings.append(result)
            return result
        else:
            return f"Unknown tool: {function_name}"

    def research(self, topic):
        """Main research workflow using tool calling"""
        print(f"🔍 Researching: {topic}")
        print("="*50)

        # Initialize conversation
        self.conversation = [
            {
                "role": "system",
                "content": "You are a research agent. Your task is to thoroughly research a topic by searching for information, analyzing findings, and creating a comprehensive summary. Use the available tools systematically."
            },
            {
                "role": "user",
                "content": f"Please research the topic '{topic}' comprehensively. Start by searching for information, then analyze your findings, and finally create a professional summary."
            }
        ]

        max_iterations = 10
        for iteration in range(max_iterations):
            print(f"\n--- Research Step {iteration + 1} ---")

            # Get response from Qwen with tools
            response = call_qwen_api(self.conversation, self.tools)
            content = response.get('content', '')
            tool_calls = response.get('tool_calls', [])

            if content:
                print(f"Agent: {content}")

            # Add assistant message to conversation
            self.conversation.append({
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls
            })

            # Check if there are tool calls to execute
            if not tool_calls:
                # No more tool calls, research is complete
                if "summary" in content.lower() or "# research" in content:
                    return content
                elif iteration > 3:  # If we've done several iterations without tool calls
                    return content
                else:
                    # Ask for more action
                    self.conversation.append({
                        "role": "user",
                        "content": "Please continue with the research process if not complete, or provide the final summary."
                    })
                    continue

            # Execute tool calls
            for tool_call in tool_calls:
                function_name = tool_call.get('function', {}).get('name')
                print(f"Executing: {function_name}")
                result = self.execute_tool_call(tool_call)
                print(f"Result: {result[:100]}..." if len(str(result)) > 100 else f"Result: {result}")

                # Add tool result to conversation
                self.conversation.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get('id', 'unknown'),
                    "content": str(result)
                })

        return "Research completed - maximum iterations reached"

def main():
    if len(sys.argv) < 2:
        print("Usage: python research_agent.py '<topic>'")
        print("Example: python research_agent.py 'AI agents in software development'")
        return

    topic = sys.argv[1]
    agent = ResearchAgent()

    try:
        summary = agent.research(topic)
        print("\n" + "="*50)
        print("📋 RESEARCH SUMMARY")
        print("="*50)
        print(summary)
    except KeyboardInterrupt:
        print("\n\n❌ Research interrupted by user")
    except Exception as e:
        print(f"\n❌ Research failed: {e}")

if __name__ == "__main__":
    main()