# Copyright (c) 2026 Dedalus Labs, Inc.
# SPDX-License-Identifier: MIT

"""Live Supermemory API connection probes."""

from __future__ import annotations

from http import HTTPStatus

import pytest
from dedalus_mcp.testing import ConnectionTester, HttpMethod
from dedalus_mcp.testing import TestRequest as Req


@pytest.mark.asyncio
async def test_list_documents(supermemory_tester: ConnectionTester) -> None:
    """Documents list endpoint should accept a minimal request."""
    resp = await supermemory_tester.request(
        Req(method=HttpMethod.POST, path="/v3/documents/list", body={"limit": 1, "page": 1})
    )

    assert resp.success, f"List documents failed: status={resp.status} body={resp.body!r}"
    assert resp.status == HTTPStatus.OK


@pytest.mark.asyncio
async def test_search(supermemory_tester: ConnectionTester) -> None:
    """v4 search endpoint should accept a minimal query."""
    resp = await supermemory_tester.request(
        Req(
            method=HttpMethod.POST,
            path="/v4/search",
            body={"q": "test", "searchMode": "hybrid", "limit": 1, "threshold": 0.5, "rerank": False},
        )
    )

    assert resp.success, f"Search failed: status={resp.status} body={resp.body!r}"
    assert resp.status == HTTPStatus.OK
