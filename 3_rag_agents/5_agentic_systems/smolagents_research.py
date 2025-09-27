# /// script
# dependencies = [
#   "smolagents[litellm]",
#   "ddgs",
# ]
# ///
"""
Smolagents Research Agent - Real web research with DuckDuckGo and Ollama
"""

from smolagents import CodeAgent, DuckDuckGoSearchTool, LiteLLMModel


def create_research_agent():
    """Create a research agent with DuckDuckGo search capabilities"""

    # Configure local Ollama model
    model = LiteLLMModel(
        model_id="ollama/qwen3:1.7b",
        extra_body={
            "think": False,
            "options": {"num_predict": 200, "temperature": 0.7},
        },
    )

    # Initialize search tool
    search_tool = DuckDuckGoSearchTool()

    # Create agent with search capabilities
    agent = CodeAgent(tools=[search_tool], model=model)

    return agent


def demonstrate_research():
    """Demonstrate research agent capabilities"""
    print("🔍 Smolagents Research Agent Demo")
    print("=" * 50)

    # Create the agent
    try:
        agent = create_research_agent()
        print("✅ Research agent initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        print("\nMake sure you have:")
        print("- smolagents installed: pip install smolagents")
        print("- Ollama running: ollama serve")
        print("- Qwen model available: ollama pull qwen3:1.7b")
        return

    # Research tasks to demonstrate
    research_topics = [
        "What are the latest developments in AI agents in 2024?",
        "How do ReAct agents work and what are their advantages?",
        "What are the best practices for deploying LLM agents in production?",
    ]

    for i, topic in enumerate(research_topics, 1):
        print(f"\n🧪 Research Task {i}: {topic}")
        print("-" * 60)

        try:
            # Run the research
            result = agent.run(
                f"Research this topic and provide a comprehensive summary: {topic}"
            )

            print("📋 Research Results:")
            print(result)

        except Exception as e:
            print(f"❌ Research failed: {e}")
            continue

        print("\n" + "=" * 60)

        # Ask user if they want to continue
        if i < len(research_topics):
            try:
                user_input = input(
                    "\nPress Enter to continue to next research task, or 'q' to quit: "
                )
                if user_input.lower().strip() == "q":
                    break
            except KeyboardInterrupt:
                print("\n\nResearch session interrupted by user.")
                break


def interactive_research():
    """Allow user to input custom research topics"""
    print("\n🎯 Interactive Research Mode")
    print("Enter your research questions (type 'quit' to exit)")

    try:
        agent = create_research_agent()
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        return

    while True:
        try:
            topic = input("\n🔍 Research topic: ").strip()

            if topic.lower() in ["quit", "exit", "q"]:
                break

            if not topic:
                print("Please enter a research topic.")
                continue

            print(f"\n🔎 Researching: {topic}")
            print("-" * 50)

            result = agent.run(
                f"Research this topic and provide a comprehensive summary: {topic}"
            )

            print("📋 Research Results:")
            print(result)

        except KeyboardInterrupt:
            print("\n\nResearch session ended.")
            break
        except Exception as e:
            print(f"❌ Research failed: {e}")
            continue


def main():
    """Main demo function"""
    print("🤖 Smolagents Research Agent")
    print("=" * 40)

    print("\nThis demo shows how to:")
    print("• Use smolagents framework with local Ollama models")
    print("• Integrate DuckDuckGo search for real web research")
    print("• Create structured agent workflows")
    print("• Handle errors and edge cases gracefully")

    # Run predefined demonstrations
    demonstrate_research()

    # Option for interactive mode
    try:
        interactive_choice = input(
            "\nWould you like to try interactive research mode? (y/N): "
        )
        if interactive_choice.lower().strip() in ["y", "yes"]:
            interactive_research()
    except KeyboardInterrupt:
        pass

    print("\n✨ Research demo completed!")
    print("\n💡 Key Takeaways:")
    print("• Smolagents simplifies agent creation with built-in tools")
    print("• Local models work well for many research tasks")
    print("• Real web search adds significant value to agents")
    print("• Proper error handling is crucial for production use")


if __name__ == "__main__":
    main()
