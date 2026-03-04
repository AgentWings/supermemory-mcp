# Copyright (c) 2026 Dedalus Labs, Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for Supermemory tool functions (monkeypatched, no network).

Endpoint contracts verified against the supermemory Python SDK v3.27.0.
"""

from __future__ import annotations

from typing import Any

import pytest
from dedalus_mcp import HttpMethod

from supermemory import (
    DocumentInput,
    MemoryInput,
    SupermemoryResult,
    supermemory_add_content,
    supermemory_batch_add_documents,
    supermemory_bulk_delete_documents,
    supermemory_create_memories,
    supermemory_delete_document,
    supermemory_forget_memory,
    supermemory_get_document,
    supermemory_get_profile,
    supermemory_list_documents,
    supermemory_search,
    supermemory_search_documents,
    supermemory_update_document,
    supermemory_update_memory,
)

# --- Helpers ---

OK = SupermemoryResult(success=True, data={"ok": True})
ERR = SupermemoryResult(success=False, error="boom")


def _fake_req(captured: dict[str, Any], result: SupermemoryResult = OK):
    """Return an async fake for ``_req`` that records calls into *captured*."""

    async def _inner(method: HttpMethod, path: str, body: Any = None) -> SupermemoryResult:
        captured["method"] = method
        captured["path"] = path
        captured["body"] = body
        return result

    return _inner


# --- Profile ---


@pytest.mark.asyncio
async def test_get_profile_minimal(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_profile should POST /v4/profile with containerTag."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    result = await supermemory_get_profile(container_tag="user_1")

    assert result.success
    assert cap["method"] == HttpMethod.POST
    assert cap["path"] == "/v4/profile"
    assert cap["body"] == {"containerTag": "user_1"}


@pytest.mark.asyncio
async def test_get_profile_with_query(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_profile should include q and threshold when provided."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_get_profile(container_tag="u", q="dark mode", threshold=0.7)

    assert cap["body"]["q"] == "dark mode"
    assert cap["body"]["threshold"] == 0.7


@pytest.mark.asyncio
async def test_get_profile_with_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_profile should forward filters (SDK: client.profile(filters=...))."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    filt = {"AND": [{"key": "role", "value": "admin"}]}
    await supermemory_get_profile(container_tag="u", filters=filt)

    assert cap["body"]["filters"] == filt


# --- Content Ingestion ---


@pytest.mark.asyncio
async def test_add_content_minimal(monkeypatch: pytest.MonkeyPatch) -> None:
    """add_content should POST /v3/documents with content and containerTag."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_add_content(content="hello", container_tag="t")

    assert cap["method"] == HttpMethod.POST
    assert cap["path"] == "/v3/documents"
    assert cap["body"] == {"content": "hello", "containerTag": "t"}


@pytest.mark.asyncio
async def test_add_content_all_optional_params(monkeypatch: pytest.MonkeyPatch) -> None:
    """add_content should include optional keys when provided."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_add_content(
        content="x",
        container_tag="t",
        custom_id="my_id",
        metadata={"env": "prod"},
        entity_context="This is a user's diary.",
    )

    body = cap["body"]
    assert body["customId"] == "my_id"
    assert body["metadata"] == {"env": "prod"}
    assert body["entityContext"] == "This is a user's diary."


@pytest.mark.asyncio
async def test_batch_add_documents(monkeypatch: pytest.MonkeyPatch) -> None:
    """batch_add should POST /v3/documents/batch with serialized DocumentInputs."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    docs = [
        DocumentInput(content="a", container_tag="t1"),
        DocumentInput(content="b", container_tag="t2", custom_id="cid", metadata={"k": "v"}),
    ]
    await supermemory_batch_add_documents(documents=docs)

    assert cap["method"] == HttpMethod.POST
    assert cap["path"] == "/v3/documents/batch"
    items = cap["body"]["documents"]
    assert len(items) == 2
    assert items[0] == {"content": "a", "containerTag": "t1"}
    assert items[1] == {"content": "b", "containerTag": "t2", "customId": "cid", "metadata": {"k": "v"}}


# --- Document Operations ---


@pytest.mark.asyncio
async def test_list_documents_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_documents should POST /v3/documents/list with defaults."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_list_documents()

    assert cap["method"] == HttpMethod.POST
    assert cap["path"] == "/v3/documents/list"
    assert cap["body"] == {"limit": 50, "page": 1}


@pytest.mark.asyncio
async def test_list_documents_with_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_documents should include containerTags when provided."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_list_documents(container_tags=["a", "b"], limit=10, page=2)

    assert cap["body"] == {"containerTags": ["a", "b"], "limit": 10, "page": 2}


@pytest.mark.asyncio
async def test_list_documents_with_sort_and_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_documents should forward sort, order, include_content, filters.

    SDK: client.documents.list(sort="createdAt", order="desc",
         include_content=True, filters={...})
    """
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    filt = {"AND": [{"key": "type", "value": "note"}]}
    await supermemory_list_documents(sort="createdAt", order="desc", include_content=True, filters=filt)

    body = cap["body"]
    assert body["sort"] == "createdAt"
    assert body["order"] == "desc"
    assert body["includeContent"] is True
    assert body["filters"] == filt


@pytest.mark.asyncio
async def test_get_document(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_document should GET /v3/documents/{id}."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_get_document(document_id="doc_42")

    assert cap["method"] == HttpMethod.GET
    assert cap["path"] == "/v3/documents/doc_42"
    assert cap["body"] is None


@pytest.mark.asyncio
async def test_update_document(monkeypatch: pytest.MonkeyPatch) -> None:
    """update_document should PATCH /v3/documents/{id}."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_update_document(document_id="doc_1", content="new", metadata={"v": 2})

    assert cap["method"] == HttpMethod.PATCH
    assert cap["path"] == "/v3/documents/doc_1"
    assert cap["body"] == {"content": "new", "metadata": {"v": 2}}


@pytest.mark.asyncio
async def test_delete_document(monkeypatch: pytest.MonkeyPatch) -> None:
    """delete_document should DELETE /v3/documents/{id}."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_delete_document(document_id="doc_99")

    assert cap["method"] == HttpMethod.DELETE
    assert cap["path"] == "/v3/documents/doc_99"


@pytest.mark.asyncio
async def test_bulk_delete_by_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """bulk_delete should DELETE /v3/documents/bulk with ids."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_bulk_delete_documents(ids=["a", "b"])

    assert cap["method"] == HttpMethod.DELETE
    assert cap["path"] == "/v3/documents/bulk"
    assert cap["body"] == {"ids": ["a", "b"]}


@pytest.mark.asyncio
async def test_bulk_delete_by_tags(monkeypatch: pytest.MonkeyPatch) -> None:
    """bulk_delete should accept containerTags instead of ids."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_bulk_delete_documents(container_tags=["user_x"])

    assert cap["body"] == {"containerTags": ["user_x"]}


# --- Search ---


@pytest.mark.asyncio
async def test_search_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Search should POST /v4/search with expected defaults."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_search(q="hello")

    assert cap["method"] == HttpMethod.POST
    assert cap["path"] == "/v4/search"
    body = cap["body"]
    assert body["q"] == "hello"
    assert body["searchMode"] == "hybrid"
    assert body["limit"] == 10
    assert body["threshold"] == 0.5
    assert body["rerank"] is False
    assert "containerTag" not in body
    assert "filters" not in body
    assert "rewriteQuery" not in body


@pytest.mark.asyncio
async def test_search_with_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Search should include containerTag and filters when provided."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    filt = {"AND": [{"key": "status", "value": "active"}]}
    await supermemory_search(q="x", container_tag="u1", filters=filt)

    assert cap["body"]["containerTag"] == "u1"
    assert cap["body"]["filters"] == filt


@pytest.mark.asyncio
async def test_search_with_rewrite_query(monkeypatch: pytest.MonkeyPatch) -> None:
    """Search (v4) should forward rewriteQuery.

    SDK: client.search.memories(rewrite_query=True)
    """
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_search(q="x", rewrite_query=True)

    assert cap["body"]["rewriteQuery"] is True


@pytest.mark.asyncio
async def test_search_documents_minimal(monkeypatch: pytest.MonkeyPatch) -> None:
    """search_documents should POST /v3/search."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_search_documents(q="test")

    assert cap["method"] == HttpMethod.POST
    assert cap["path"] == "/v3/search"
    assert cap["body"]["q"] == "test"
    for key in ("includeFullDocs", "includeSummary", "onlyMatchingChunks", "rewriteQuery"):
        assert key not in cap["body"]


@pytest.mark.asyncio
async def test_search_documents_all_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    """search_documents should forward all boolean/threshold options."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_search_documents(
        q="q",
        container_tags=["t"],
        rerank=True,
        rewrite_query=True,
        include_full_docs=True,
        include_summary=True,
        only_matching_chunks=True,
        chunk_threshold=0.8,
        document_threshold=0.6,
        doc_id="doc_1",
        filters={"AND": []},
    )

    body = cap["body"]
    assert body["containerTags"] == ["t"]
    assert body["rerank"] is True
    assert body["rewriteQuery"] is True
    assert body["includeFullDocs"] is True
    assert body["includeSummary"] is True
    assert body["onlyMatchingChunks"] is True
    assert body["chunkThreshold"] == 0.8
    assert body["documentThreshold"] == 0.6
    assert body["docId"] == "doc_1"
    assert body["filters"] == {"AND": []}


# --- Memory Operations ---


@pytest.mark.asyncio
async def test_create_memories(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_memories should serialize MemoryInputs with camelCase keys."""
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    memories = [
        MemoryInput(content="likes dark mode", is_static=True),
        MemoryInput(content="had coffee today", metadata={"mood": "good"}),
    ]
    await supermemory_create_memories(memories=memories, container_tag="u1")

    assert cap["method"] == HttpMethod.POST
    assert cap["path"] == "/v4/memories"
    items = cap["body"]["memories"]
    assert items[0] == {"content": "likes dark mode", "isStatic": True}
    assert items[1] == {"content": "had coffee today", "isStatic": False, "metadata": {"mood": "good"}}
    assert cap["body"]["containerTag"] == "u1"


@pytest.mark.asyncio
async def test_forget_memory_by_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """forget_memory should DELETE /v4/memories with containerTag and id in body.

    SDK: client.memories.forget(container_tag=..., id=...)
    Verified: MemoriesResource.forget() calls self._delete("/v4/memories", body=...)
    """
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_forget_memory(container_tag="user_1", memory_id="mem_abc123")

    assert cap["method"] == HttpMethod.DELETE
    assert cap["path"] == "/v4/memories"
    assert cap["body"] == {"containerTag": "user_1", "id": "mem_abc123"}


@pytest.mark.asyncio
async def test_forget_memory_by_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """forget_memory should accept content match instead of id.

    SDK: client.memories.forget(container_tag=..., content=...)
    """
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_forget_memory(container_tag="u", content="likes cats")

    body = cap["body"]
    assert "id" not in body
    assert body["containerTag"] == "u"
    assert body["content"] == "likes cats"


@pytest.mark.asyncio
async def test_forget_memory_with_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    """forget_memory should include optional reason.

    SDK: client.memories.forget(container_tag=..., id=..., reason=...)
    """
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_forget_memory(container_tag="u", memory_id="mem_1", reason="user requested deletion")

    assert cap["body"]["reason"] == "user requested deletion"


@pytest.mark.asyncio
async def test_update_memory_by_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """update_memory should PATCH /v4/memories with containerTag and id.

    SDK: client.memories.update_memory(container_tag=..., new_content=..., id=...)
    """
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_update_memory(container_tag="user_1", new_content="updated", memory_id="mem_1")

    assert cap["method"] == HttpMethod.PATCH
    assert cap["path"] == "/v4/memories"
    assert cap["body"] == {"containerTag": "user_1", "newContent": "updated", "id": "mem_1"}


@pytest.mark.asyncio
async def test_update_memory_by_content(monkeypatch: pytest.MonkeyPatch) -> None:
    """update_memory should accept content match instead of id.

    SDK: client.memories.update_memory(container_tag=..., new_content=..., content=...)
    """
    cap: dict[str, Any] = {}
    monkeypatch.setattr("supermemory._req", _fake_req(cap))

    await supermemory_update_memory(container_tag="u", new_content="v2", content="v1", metadata={"rev": 2})

    body = cap["body"]
    assert "id" not in body
    assert body["containerTag"] == "u"
    assert body["content"] == "v1"
    assert body["newContent"] == "v2"
    assert body["metadata"] == {"rev": 2}


# --- Error propagation ---


@pytest.mark.asyncio
async def test_error_propagation(monkeypatch: pytest.MonkeyPatch) -> None:
    """All tools should propagate _req errors as typed SupermemoryResult."""
    monkeypatch.setattr("supermemory._req", _fake_req({}, result=ERR))

    result = await supermemory_get_document(document_id="missing")

    assert isinstance(result, SupermemoryResult)
    assert not result.success
    assert result.error == "boom"
