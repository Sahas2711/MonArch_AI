"""
Monarch — Production-Level Multi-Agent System CLI Entrypoint.

Usage:
    python main.py                              # Interactive chat loop
    python main.py --ingest ./doc.pdf --user-id u1  # Ingest document into RAG store
    python main.py --serve-mcp                  # Launch MCP server over HTTP
"""

import argparse
import asyncio
import sys
from langchain_core.messages import HumanMessage
from Agents.graph import graph
from MCP.server import run_mcp_server
from RAG.manager import rag_manager


async def chat_loop():
    config = {"configurable": {"thread_id": "cli-session"}}
    print("Monarch ready. Type a message ('exit' to quit).")
    while True:
        try:
            user_inp = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_inp or user_inp.lower() in {"exit", "quit"}:
            break

        result = await graph.ainvoke(
            {
                "user_inp": user_inp,
                "messages": [HumanMessage(content=user_inp)],
                "user_id": None,
                "output": "",
                "context": "",
                "route": "",
            },
            config=config,
        )
        print(f"monarch> {result['output']}")


def main():
    parser = argparse.ArgumentParser(description="Monarch multi-agent system")
    parser.add_argument("--ingest", help="Path to a document to ingest into the RAG store")
    parser.add_argument("--user-id", default=None, help="Owner tag for ingested documents")
    parser.add_argument("--serve-mcp", action="store_true", help="Run as an MCP server instead of a chat loop")
    parser.add_argument("--serve-api", action="store_true", help="Run as FastAPI backend server")
    parser.add_argument("--run-harness", action="store_true", help="Run automated evaluation test harness suite")
    args = parser.parse_args()

    if args.run_harness:
        from harness.eval_suite import run_benchmark_harness
        asyncio.run(run_benchmark_harness())
        return

    if args.ingest:
        result = rag_manager.ingest(args.ingest, user_id=args.user_id)
        print(result)
        return

    if args.serve_mcp:
        run_mcp_server()
        return

    if args.serve_api:
        import uvicorn
        uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
        return

    asyncio.run(chat_loop())


if __name__ == "__main__":
    main()
