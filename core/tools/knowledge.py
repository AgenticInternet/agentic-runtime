"""
Knowledge Base Tools
====================
Tools for RAG (Retrieval-Augmented Generation) and knowledge base integration.
"""

from typing import Any, List, Optional

from ..policies import AgentSpec


def build_knowledge_tools(spec: AgentSpec) -> List[Any]:
    """
    Build knowledge base tools based on spec configuration.

    Supports multiple vector databases and embedders:
    - LanceDB (default, file-based)
    - PgVector (PostgreSQL)
    - Chroma
    - Qdrant

    Args:
        spec: Agent specification with knowledge policy

    Returns:
        List of knowledge tools
    """
    if not spec.knowledge.enabled:
        return []

    tools: List[Any] = []

    # Import based on vector_db selection
    vector_db = spec.knowledge.vector_db
    embedder_type = spec.knowledge.embedder

    try:
        # Build embedder
        embedder = _build_embedder(embedder_type, spec.knowledge.embedder_model)

        # Build vector database
        if vector_db == "lancedb":
            from agno.vectordb.lancedb import LanceDb
            from agno.vectordb.search import SearchType

            search_type_map = {
                "vector": SearchType.vector,
                "keyword": SearchType.keyword,
                "hybrid": SearchType.hybrid,
            }

            vector_db_instance = LanceDb(
                uri=spec.knowledge.vector_db_uri,
                table_name=spec.knowledge.table_name,
                search_type=search_type_map.get(spec.knowledge.search_type, SearchType.hybrid),
                embedder=embedder,
            )

        elif vector_db == "pgvector":
            from agno.vectordb.pgvector import PgVector

            vector_db_instance = PgVector(
                db_url=spec.knowledge.vector_db_uri,
                table_name=spec.knowledge.table_name,
                embedder=embedder,
            )

        elif vector_db == "chroma":
            from agno.vectordb.chroma import ChromaDb

            vector_db_instance = ChromaDb(
                path=spec.knowledge.vector_db_uri,
                collection=spec.knowledge.table_name,
                embedder=embedder,
            )

        elif vector_db == "qdrant":
            from agno.vectordb.qdrant import Qdrant

            vector_db_instance = Qdrant(
                url=spec.knowledge.vector_db_uri,
                collection=spec.knowledge.table_name,
                embedder=embedder,
            )

        else:
            raise ValueError(f"Unsupported vector database: {vector_db}")

        # Build knowledge base
        from agno.knowledge.knowledge import Knowledge

        knowledge = Knowledge(
            vector_db=vector_db_instance,
            max_results=spec.knowledge.max_results,
        )

        # Load content sources if specified
        for source in spec.knowledge.content_sources:
            if source.startswith(("http://", "https://")):
                knowledge.add_content(url=source)
            else:
                knowledge.add_content(path=source)

        # Create knowledge tools
        from agno.tools.knowledge import KnowledgeTools

        tools.append(KnowledgeTools(knowledge=knowledge))

    except ImportError as e:
        # Log warning but don't fail - knowledge tools are optional
        import warnings
        warnings.warn(f"Could not import knowledge dependencies: {e}")

    return tools


def _build_embedder(embedder_type: str, model_id: Optional[str] = None) -> Any:
    """Build embedder based on type and optional model ID."""

    if embedder_type == "openai":
        from agno.knowledge.embedder.openai import OpenAIEmbedder

        if model_id:
            return OpenAIEmbedder(id=model_id)
        return OpenAIEmbedder(id="text-embedding-3-small")

    elif embedder_type == "sentence-transformer":
        from agno.knowledge.embedder.sentence_transformer import SentenceTransformerEmbedder

        if model_id:
            return SentenceTransformerEmbedder(id=model_id)
        return SentenceTransformerEmbedder()

    elif embedder_type == "voyage":
        from agno.knowledge.embedder.voyageai import VoyageAIEmbedder

        if model_id:
            return VoyageAIEmbedder(id=model_id)
        return VoyageAIEmbedder()

    elif embedder_type == "azure-openai":
        from agno.knowledge.embedder.azure_openai import AzureOpenAIEmbedder

        if model_id:
            return AzureOpenAIEmbedder(id=model_id)
        return AzureOpenAIEmbedder()

    else:
        raise ValueError(f"Unsupported embedder type: {embedder_type}")
