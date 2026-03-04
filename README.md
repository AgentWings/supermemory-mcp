# Supermemory MCP Server

A Dedalus MCP server for AI memory and context retrieval via Supermemory.

## Features

- **Profile**: AI-generated user profiles from stored memories (static traits + dynamic context)
- **Content Ingestion**: Add text, URLs, and conversations; batch ingestion support
- **Documents**: Full CRUD with bulk delete
- **Search**: v4 hybrid search (memories + chunks) and v3 document search with chunk-level control
- **Memories**: Create, update, and forget structured memories directly

## Authentication

This server uses a Bearer API key from [console.supermemory.ai](https://console.supermemory.ai).

## Tools

| Tool | Description |
|------|-------------|
| `supermemory_get_profile` | AI-generated user profile with static traits and dynamic context |
| `supermemory_add_content` | Ingest text, URLs, or conversations with entity context |
| `supermemory_batch_add_documents` | Batch-ingest multiple documents in one request |
| `supermemory_list_documents` | List documents with optional filtering |
| `supermemory_get_document` | Get a document and its processing status |
| `supermemory_update_document` | Update a document's content or metadata |
| `supermemory_delete_document` | Permanently delete a document |
| `supermemory_bulk_delete_documents` | Bulk-delete by IDs or container tags |
| `supermemory_search` | Semantic search with metadata filters (v4, recommended) |
| `supermemory_search_documents` | Document search with chunk-level control (v3) |
| `supermemory_create_memories` | Create memories directly from known facts |
| `supermemory_forget_memory` | Soft-delete a memory |
| `supermemory_update_memory` | Update a memory (versioned) |

## Usage

```python
from dedalus_labs import DedalusRunner

runner = DedalusRunner()
result = await runner.run(
    input="Store that I prefer dark mode and search my preferences",
    model="openai/gpt-4.1",
    mcp_servers=["windsor/supermemory-mcp"],
)
```

## License

MIT
