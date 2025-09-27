# Use Case: Coding CLI

Today we'll explore how AI-powered coding CLIs are transforming software development. These tools act as intelligent pair programmers that can understand context, write code, and make changes across entire codebases.

---

## Demo: Claude Code

Let's start by demonstrating Claude Code, Anthropic's official CLI tool.

First, ensure Claude Code is installed:

```bash
npm install -g @anthropic-ai/claude-code
```

Create a simple Python project to demonstrate:

```bash
mkdir weather-app && cd weather-app
```

Now, let's use Claude Code to build a weather application:

```bash
claude "Create a Python CLI app that fetches weather data for a given city. Use the OpenWeatherMap API and include error handling."
```

---

Watch as Claude Code:

- Creates the necessary Python files
- Sets up proper project structure
- Implements API integration with error handling
- Adds command-line argument parsing

You can ask Claude Code to make improvements:

```bash
claude "Add caching to avoid repeated API calls for the same city within 10 minutes"
```

Claude Code understands context and can work across multiple files:

```bash
claude "Add unit tests for the weather fetching functionality"
```

## Demo: Aider

Now let's demonstrate Aider, another powerful AI coding assistant.

Install Aider:

```bash
uv tool install --force --python python3.12 --with pip aider-chat@latest
```

Navigate to your project and start Aider:

```bash
aider
```

In the Aider session, demonstrate these capabilities:

---

Ask Aider to refactor the code:

```
/add weather.py
refactor the weather fetching logic into separate functions for API calls and data parsing
```

Aider can work with git:

```
make the changes and create a descriptive commit message
```

Show how Aider handles complex requests:

```
add a feature to display a 5-day forecast instead of just current weather
```

---

## Key Differences

**Claude Code:**

- Optimized for rapid prototyping and code generation
- Excellent at understanding high-level requirements
- Strong integration with modern development workflows
- Great at creating new features or files
- Some neat new features like claude commands and agents.

**Aider:**

- Specialized in code editing and refactoring
- Deep git integration
- Excellent for iterative development
- Great at modifying existing codebases

---

## Resources

- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [Aider Documentation](https://aider.chat/)
- [Comparison of AI Coding Assistants](https://github.com/paul-gauthier/aider#comparisons)
