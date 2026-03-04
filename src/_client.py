# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Sample MCP client for Supermemory.

Environment variables:
    DEDALUS_API_KEY: Your Dedalus API key (dsk_*)
    DEDALUS_API_URL: Product API base URL
    DEDALUS_AS_URL: Authorization server URL
"""

import asyncio
import os
import webbrowser

from dotenv import load_dotenv

load_dotenv()

from dedalus_labs import AsyncDedalus, AuthenticationError, DedalusRunner  # noqa: E402
from dedalus_labs.utils.stream import stream_async  # noqa: E402


class MissingEnvError(ValueError):
    """Required environment variable not set."""


def get_env(key: str) -> str:
    """Get required env var or raise."""
    val = os.getenv(key)
    if not val:
        raise MissingEnvError(key)
    return val


API_URL = get_env("DEDALUS_API_URL")
AS_URL = get_env("DEDALUS_AS_URL")
DEDALUS_API_KEY = os.getenv("DEDALUS_API_KEY")

print("=== Environment ===")
print(f"  DEDALUS_API_URL: {API_URL}")
print(f"  DEDALUS_AS_URL: {AS_URL}")
print(f"  DEDALUS_API_KEY: {DEDALUS_API_KEY[:20]}..." if DEDALUS_API_KEY else "  DEDALUS_API_KEY: None")


def _extract_connect_url(err: AuthenticationError) -> str | None:
    """Pull the OAuth connect URL from an AuthenticationError, if present."""
    body = err.body if isinstance(err.body, dict) else {}
    return body.get("connect_url") or body.get("detail", {}).get("connect_url")


def _prompt_oauth(url: str) -> None:
    """Open OAuth URL in browser and block until user confirms."""
    print("\nAttempting to open your default browser.")
    print("If the browser does not open, open the following URL:\n")
    print(url)
    webbrowser.open(url)
    input("\nPress Enter after completing OAuth...")


async def run_agent_loop() -> None:
    """Interactive agent loop with streaming."""
    client = AsyncDedalus(api_key=DEDALUS_API_KEY, base_url=API_URL, as_base_url=AS_URL)
    runner = DedalusRunner(client)
    messages: list[dict] = []

    async def run_turn() -> None:
        stream = runner.run(
            input=messages, model="anthropic/claude-opus-4-5", mcp_servers=["windsor/supermemory-mcp"], stream=True
        )
        print("\nAssistant: ", end="", flush=True)
        await stream_async(stream)

    print("\n=== Supermemory MCP Agent ===")
    print("Type 'quit' or 'exit' to end the session.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        messages.append({"role": "user", "content": user_input})

        try:
            await run_turn()
        except AuthenticationError as e:
            url = _extract_connect_url(e)
            if not url:
                raise
            _prompt_oauth(url)
            await run_turn()

        print()


async def main() -> None:
    """Run interactive agent loop."""
    await run_agent_loop()


if __name__ == "__main__":
    asyncio.run(main())
