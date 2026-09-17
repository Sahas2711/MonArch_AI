"""
Monarch — Multi-Agent Orchestration System (Backward-compatibility wrapper).

This module re-exports components from the modular packages:
  - Agents/ : State, router, graph, planner, research_agent, rag_agent
  - RAG/    : RAGAgentManager, rag_manager
  - MCP/    : run_mcp_server
  - SQL/    : MemoryRepository, memory_repo
  - utils/  : config, logger, llm_retry, eval
"""

from Agents.graph import build_graph, graph
from Agents.planner import planner
from Agents.rag import rag_agent
from Agents.research import research_agent
from Agents.router import orchestrator, route_next_node
from Agents.state import RouteDecision, State
from MCP.server import run_mcp_server
from RAG.manager import RAGAgentManager, rag_manager
from SQL.repository import MemoryRepository, memory_repo
from main import chat_loop, main
from utils.config import EMBEDDING_MODEL, GROQ_API_KEY, GROQ_MODEL, UNSTRUCTURED_API_KEY, llm
from utils.eval import run_eval
from utils.logger import log
from utils.retry import llm_retry

__all__ = [
    "State",
    "RouteDecision",
    "orchestrator",
    "route_next_node",
    "planner",
    "research_agent",
    "rag_agent",
    "RAGAgentManager",
    "rag_manager",
    "build_graph",
    "graph",
    "run_eval",
    "run_mcp_server",
    "chat_loop",
    "main",
    "MemoryRepository",
    "memory_repo",
    "log",
    "llm",
    "llm_retry",
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "EMBEDDING_MODEL",
    "UNSTRUCTURED_API_KEY",
]

if __name__ == "__main__":
    main()