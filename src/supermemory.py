# Copyright (c) 2026 Dedalus Labs, Inc.
# SPDX-License-Identifier: MIT

"""Supermemory API tools for supermemory-mcp.

AI memory infrastructure: store, search, and manage long-term context.
Ref: https://docs.supermemory.ai
"""

from dataclasses import dataclass, field
from typing import Any, TypeAlias

from dedalus_mcp import HttpMethod, HttpRequest, get_context, tool
from dedalus_mcp.auth import Connection, SecretKeys
from dedalus_mcp.types import ToolAnnotations
from pydantic import BaseModel

# --- Connection ---

supermemory = Connection(
    name="supermemory-mcp",
    secrets=SecretKeys(token="SUPERMEMORY_API_KEY"),
    base_url="https://api.supermemory.ai",
    auth_header_format="Bearer {api_key}",
)

# --- Types ---

MetadataValue: TypeAlias = str | int | float | bool
Metadata: TypeAlias = dict[str, MetadataValue]


@dataclass(frozen=True)
class SupermemoryResult:
    """Standardized Supermemory API response."""

    success: bool
    data: Any = None
    meta: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class MemoryInput(BaseModel):
    """A single memory to create directly."""

    content: str
    is_static: bool = False
    metadata: Metadata | None = None


class DocumentInput(BaseModel):
    """A single document for batch ingestion."""

    content: str
    container_tag: str
    custom_id: str | None = None
    metadata: Metadata | None = None


# --- Helpers ---


async def _req(method: HttpMethod, path: str, body: Any = None) -> SupermemoryResult:
    """Execute Supermemory API request and normalize the response."""
    ctx = get_context()
    resp = await ctx.dispatch("supermemory-mcp", HttpRequest(method=method, path=path, body=body))
    if resp.success and resp.response:
        return SupermemoryResult(success=True, data=resp.response.body)
    if not resp.success:
        return SupermemoryResult(success=False, error=resp.error.message if resp.error else "Request failed")
    return SupermemoryResult(success=True)


# --- Profile ---


@tool(
    description="Get an AI-generated user profile with static traits and dynamic context",
    tags=["profile", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def supermemory_get_profile(
    container_tag: str, q: str | None = None, threshold: float | None = None, filters: dict[str, Any] | None = None
) -> SupermemoryResult:
    """Build a user profile from stored memories.

    Returns static traits (persistent facts) and dynamic context
    (recently relevant information). Optionally enriches the profile
    with search results when ``q`` is provided.

    Args:
        container_tag: User or project scope (e.g. "user_123").
        q: Optional query to include relevant search results.
        threshold: Similarity cutoff 0-1 (higher = stricter match).
        filters: Metadata filter with AND/OR keys.

    """
    payload: dict[str, Any] = {"containerTag": container_tag}
    if q is not None:
        payload["q"] = q
    if threshold is not None:
        payload["threshold"] = threshold
    if filters is not None:
        payload["filters"] = filters
    return await _req(HttpMethod.POST, "/v4/profile", payload)


# --- Content Ingestion ---


@tool(
    description="Add content (text, URL, conversation) to Supermemory for processing and memory extraction",
    tags=["content", "write"],
)
async def supermemory_add_content(
    content: str,
    container_tag: str,
    custom_id: str | None = None,
    metadata: Metadata | None = None,
    entity_context: str | None = None,
) -> SupermemoryResult:
    """Ingest content into Supermemory.

    Content type is auto-detected: plain text, URL, or conversation
    transcript. Supplying a ``custom_id`` that already exists will
    update the existing document instead of creating a new one.

    Args:
        content: Text, URL, or conversation to ingest.
        container_tag: User or project scope (e.g. "user_123").
        custom_id: Your own ID for deduplication and updates.
        metadata: Key-value metadata (strings, numbers, booleans only).
        entity_context: Hint for memory extraction (max 1500 chars).
            Sets default extraction context for this container tag.

    """
    payload: dict[str, Any] = {"content": content, "containerTag": container_tag}
    if custom_id is not None:
        payload["customId"] = custom_id
    if metadata is not None:
        payload["metadata"] = metadata
    if entity_context is not None:
        payload["entityContext"] = entity_context
    return await _req(HttpMethod.POST, "/v3/documents", payload)


@tool(description="Add multiple documents in a single request", tags=["content", "write"])
async def supermemory_batch_add_documents(documents: list[DocumentInput]) -> SupermemoryResult:
    """Batch-ingest multiple documents at once.

    More efficient than individual ``supermemory_add_content`` calls
    when ingesting many items.

    Args:
        documents: List of documents to ingest.

    """
    documents = [d if isinstance(d, DocumentInput) else DocumentInput.model_validate(d) for d in documents]
    payload = {
        "documents": [
            {
                "content": doc.content,
                "containerTag": doc.container_tag,
                **({"customId": doc.custom_id} if doc.custom_id else {}),
                **({"metadata": doc.metadata} if doc.metadata else {}),
            }
            for doc in documents
        ]
    }
    return await _req(HttpMethod.POST, "/v3/documents/batch", payload)


# --- Document Operations ---


@tool(
    description="List ingested documents with optional filtering by container tag",
    tags=["documents", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def supermemory_list_documents(
    container_tags: list[str] | None = None,
    limit: int = 50,
    page: int = 1,
    sort: str | None = None,
    order: str | None = None,
    include_content: bool = False,
    filters: dict[str, Any] | None = None,
) -> SupermemoryResult:
    """List documents.

    Args:
        container_tags: Filter by one or more container tags.
        limit: Items per page (max 200).
        page: Page number (1-indexed).
        sort: Sort field: "createdAt" or "updatedAt".
        order: Sort direction: "asc" or "desc".
        include_content: Include full document content in results.
        filters: Metadata filter with AND/OR keys.

    """
    payload: dict[str, Any] = {"limit": limit, "page": page}
    if container_tags:
        payload["containerTags"] = container_tags
    if sort is not None:
        payload["sort"] = sort
    if order is not None:
        payload["order"] = order
    if include_content:
        payload["includeContent"] = True
    if filters is not None:
        payload["filters"] = filters
    return await _req(HttpMethod.POST, "/v3/documents/list", payload)


@tool(
    description="Get a specific document and its processing status",
    tags=["documents", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def supermemory_get_document(document_id: str) -> SupermemoryResult:
    """Get document by ID.

    Args:
        document_id: The document ID.

    """
    return await _req(HttpMethod.GET, f"/v3/documents/{document_id}")


@tool(description="Update an existing document's content or metadata", tags=["documents", "write"])
async def supermemory_update_document(
    document_id: str, content: str | None = None, metadata: Metadata | None = None
) -> SupermemoryResult:
    """Update a document in place.

    Args:
        document_id: The document ID to update.
        content: New content replacing the existing content.
        metadata: New metadata replacing the existing metadata.

    """
    payload: dict[str, Any] = {}
    if content is not None:
        payload["content"] = content
    if metadata is not None:
        payload["metadata"] = metadata
    return await _req(HttpMethod.PATCH, f"/v3/documents/{document_id}", payload)


@tool(
    description="Delete a document permanently",
    tags=["documents", "write"],
    annotations=ToolAnnotations(destructiveHint=True),
)
async def supermemory_delete_document(document_id: str) -> SupermemoryResult:
    """Delete a document. This is permanent and cannot be undone.

    Args:
        document_id: The document ID to delete.

    """
    return await _req(HttpMethod.DELETE, f"/v3/documents/{document_id}")


@tool(
    description="Bulk-delete documents by IDs or container tags",
    tags=["documents", "write"],
    annotations=ToolAnnotations(destructiveHint=True),
)
async def supermemory_bulk_delete_documents(
    ids: list[str] | None = None, container_tags: list[str] | None = None
) -> SupermemoryResult:
    """Bulk-delete documents. Provide document IDs, container tags, or both.

    Args:
        ids: Document IDs to delete.
        container_tags: Delete all documents under these container tags.

    """
    payload: dict[str, Any] = {}
    if ids is not None:
        payload["ids"] = ids
    if container_tags is not None:
        payload["containerTags"] = container_tags
    return await _req(HttpMethod.DELETE, "/v3/documents/bulk", payload)


# --- Search ---


@tool(
    description="Semantic search across memories and document chunks (v4, recommended)",
    tags=["search", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def supermemory_search(
    q: str,
    container_tag: str | None = None,
    search_mode: str = "hybrid",
    limit: int = 10,
    threshold: float = 0.5,
    rerank: bool = False,
    rewrite_query: bool = False,
    filters: dict[str, Any] | None = None,
) -> SupermemoryResult:
    """Search memories and document chunks.

    Args:
        q: Natural-language search query.
        container_tag: Filter by user or project scope.
        search_mode: "hybrid" | "memories" | "documents".
        limit: Max results to return.
        threshold: Similarity cutoff 0-1 (higher = fewer, better matches).
        rerank: Re-score for better relevance (~100ms extra latency).
        rewrite_query: Let the API rephrase the query for better recall.
        filters: Metadata filter with AND/OR keys, e.g.
            ``{"AND": [{"key": "status", "value": "published"}]}``.

    """
    payload: dict[str, Any] = {
        "q": q,
        "searchMode": search_mode,
        "limit": limit,
        "threshold": threshold,
        "rerank": rerank,
    }
    if container_tag is not None:
        payload["containerTag"] = container_tag
    if rewrite_query:
        payload["rewriteQuery"] = True
    if filters is not None:
        payload["filters"] = filters
    return await _req(HttpMethod.POST, "/v4/search", payload)


@tool(
    description="Search documents with chunk-level control (v3)",
    tags=["search", "read"],
    annotations=ToolAnnotations(readOnlyHint=True),
)
async def supermemory_search_documents(
    q: str,
    container_tags: list[str] | None = None,
    limit: int = 10,
    rerank: bool = False,
    rewrite_query: bool = False,
    include_full_docs: bool = False,
    include_summary: bool = False,
    only_matching_chunks: bool = False,
    chunk_threshold: float | None = None,
    document_threshold: float | None = None,
    doc_id: str | None = None,
    filters: dict[str, Any] | None = None,
) -> SupermemoryResult:
    """Search at the document level with fine-grained chunk retrieval.

    Unlike ``supermemory_search`` (v4), this endpoint operates on
    documents and gives control over chunk inclusion and thresholds.

    Args:
        q: Natural-language search query.
        container_tags: Filter by one or more container tags.
        limit: Max results to return.
        rerank: Re-score for better relevance.
        rewrite_query: Let the API rephrase the query for better recall.
        include_full_docs: Return full document content (expensive).
        include_summary: Include AI-generated document summaries.
        only_matching_chunks: Return only the chunks that matched.
        chunk_threshold: Minimum chunk similarity 0-1.
        document_threshold: Minimum document-level similarity 0-1.
        doc_id: Restrict search to a single document.
        filters: Metadata filter with AND/OR keys.

    """
    payload: dict[str, Any] = {"q": q, "limit": limit, "rerank": rerank}
    if container_tags is not None:
        payload["containerTags"] = container_tags
    if rewrite_query:
        payload["rewriteQuery"] = True
    if include_full_docs:
        payload["includeFullDocs"] = True
    if include_summary:
        payload["includeSummary"] = True
    if only_matching_chunks:
        payload["onlyMatchingChunks"] = True
    if chunk_threshold is not None:
        payload["chunkThreshold"] = chunk_threshold
    if document_threshold is not None:
        payload["documentThreshold"] = document_threshold
    if doc_id is not None:
        payload["docId"] = doc_id
    if filters is not None:
        payload["filters"] = filters
    return await _req(HttpMethod.POST, "/v3/search", payload)


# --- Memory Operations (v4) ---


@tool(description="Create memories directly (for known facts, preferences, traits)", tags=["memories", "write"])
async def supermemory_create_memories(memories: list[MemoryInput], container_tag: str) -> SupermemoryResult:
    """Create memories without document ingestion.

    Use for known facts, user preferences, or static traits that
    should be stored immediately rather than extracted from text.

    Args:
        memories: Memories to create.
        container_tag: User or project scope.

    """
    memories = [m if isinstance(m, MemoryInput) else MemoryInput.model_validate(m) for m in memories]
    return await _req(
        HttpMethod.POST,
        "/v4/memories",
        {
            "memories": [
                {"content": m.content, "isStatic": m.is_static, **({"metadata": m.metadata} if m.metadata else {})}
                for m in memories
            ],
            "containerTag": container_tag,
        },
    )


@tool(description="Soft-delete a memory (excluded from search, preserved in system)", tags=["memories", "write"])
async def supermemory_forget_memory(
    container_tag: str, memory_id: str | None = None, content: str | None = None, reason: str | None = None
) -> SupermemoryResult:
    """Forget a memory. Identify it by ``memory_id`` or ``content``.

    The memory is excluded from future search results but remains
    in the system and can potentially be restored.

    Args:
        container_tag: User or project scope (required).
        memory_id: The memory ID (e.g. "mem_abc123").
        content: Exact content match (alternative to memory_id).
        reason: Optional reason for forgetting this memory.

    """
    payload: dict[str, Any] = {"containerTag": container_tag}
    if memory_id is not None:
        payload["id"] = memory_id
    if content is not None:
        payload["content"] = content
    if reason is not None:
        payload["reason"] = reason
    return await _req(HttpMethod.DELETE, "/v4/memories", payload)


@tool(description="Update a memory with new content (versioned, original preserved)", tags=["memories", "write"])
async def supermemory_update_memory(
    container_tag: str,
    new_content: str,
    memory_id: str | None = None,
    content: str | None = None,
    metadata: Metadata | None = None,
) -> SupermemoryResult:
    """Update a memory by creating a new version.

    Provide either ``memory_id`` or ``content`` to identify the
    target memory. The original version is preserved.

    Args:
        container_tag: User or project scope (required).
        new_content: The updated memory text.
        memory_id: Memory ID to update (provide this or content).
        content: Original content to match (alternative to memory_id).
        metadata: Updated metadata.

    """
    payload: dict[str, Any] = {"containerTag": container_tag, "newContent": new_content}
    if memory_id is not None:
        payload["id"] = memory_id
    if content is not None:
        payload["content"] = content
    if metadata is not None:
        payload["metadata"] = metadata
    return await _req(HttpMethod.PATCH, "/v4/memories", payload)


# --- Export ---

supermemory_tools = [
    # Profile
    supermemory_get_profile,
    # Content ingestion
    supermemory_add_content,
    supermemory_batch_add_documents,
    # Documents
    supermemory_list_documents,
    supermemory_get_document,
    supermemory_update_document,
    supermemory_delete_document,
    supermemory_bulk_delete_documents,
    # Search
    supermemory_search,
    supermemory_search_documents,
    # Memories
    supermemory_create_memories,
    supermemory_forget_memory,
    supermemory_update_memory,
]
