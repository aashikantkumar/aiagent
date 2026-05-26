# Agent package — LangGraph state machine, nodes, schemas, and prompts
#
# New modules (Architecture §2, §4, §6, §9):
#   context_manager  — Token counting, context pruning, budget allocation
#   memory           — Short/long-term memory with compression
#   error_analyzer   — Error classification, stack trace parsing, self-healing
#   workspace_indexer — File indexing, dependency graph, architecture detection
#   document_processor — PDF/DOCX/MD parsing, semantic chunking
#   embedding_engine   — Vector storage (ChromaDB), RAG retrieval
#   web_search       — DuckDuckGo web search + page content extraction
#   research_node    — Pre-build research: scaffolding commands, versions, best practices
#   judge_node       — Plan validation, architectural safety and sanity checks
