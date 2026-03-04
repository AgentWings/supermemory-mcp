# Copyright (c) 2026 Dedalus Labs, Inc.
# SPDX-License-Identifier: MIT

"""Shared pytest fixtures for supermemory-mcp tests."""

from __future__ import annotations

import os

import pytest
from dedalus_mcp.testing import ConnectionTester
from dotenv import load_dotenv

from supermemory import supermemory


@pytest.fixture(scope="session")
def supermemory_tester() -> ConnectionTester:
    """Return a locally configured ConnectionTester for the Supermemory API."""
    load_dotenv()
    if not os.getenv("SUPERMEMORY_API_KEY"):
        pytest.skip("SUPERMEMORY_API_KEY not set; skipping live tests")
    return ConnectionTester.from_env(supermemory)
