# Monarch — Contributing Guide

## Development Setup

1. Fork and clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and configure

## Code Style

- Follow PEP 8 for Python code
- Use type hints for function signatures
- Keep functions focused and under 50 lines where possible
- Use descriptive variable names

## Project Structure

```
├── api.py              # FastAPI endpoints
├── main.py             # CLI entrypoint
├── agent.py            # Backward-compat re-exports
├── Agents/             # LangGraph agent pipeline
│   ├── graph.py        # StateGraph definition
│   ├── router.py       # Query classification
│   ├── planner.py      # General reasoning
│   ├── research.py     # Web search
│   ├── rag.py          # Document retrieval
│   ├── vision.py       # Image analysis
│   ├── reflection.py   # Self-correction
│   └── state.py        # State TypedDict
├── RAG/                # Retrieval-Augmented Generation
├── SQL/                # Database layer
├── MCP/                # Model Context Protocol server
├── utils/              # Shared utilities
├── guardrails/         # Input/output validation
├── harness/            # Evaluation suite
├── static/             # Frontend assets
├── evidence/           # Demo evidence files
└── incidents/          # Case study markdown files
```

## Making Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes with clear commits

3. Run the application to verify:
   ```bash
   python api.py
   ```

4. Run the evaluation harness if applicable:
   ```bash
   python -m harness.eval_suite
   ```

5. Push and create a pull request

## Pull Request Guidelines

- Provide a clear description of changes
- Reference any related issues
- Include screenshots for UI changes
- Ensure the application starts without errors
- Add tests for new functionality when possible

## Reporting Issues

- Use the GitHub issue tracker
- Include steps to reproduce
- Provide error messages and logs
- Specify Python version and OS
