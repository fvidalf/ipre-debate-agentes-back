# Debate Agents API Documentation

## Overview

A FastAPI-based backend service for AI-powered debates between multiple agents with configurable personalities and language models.

## Base URL

```
http://localhost:8000
```

## Authentication

The API uses JWT token-based authentication via httpOnly cookies for all endpoints except login.

### Login

#### `POST /auth/login`

Login with email and password to receive authentication via httpOnly cookie.

**Request Body (form-data):**
```
username: test@example.com
password: password123
```

**Response:**
```json
{
  "message": "Login successful",
  "user": {
    "email": "test@example.com",
    "id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Cookie Set:**
- `access_token`: JWT token (httpOnly, secure in production)
- `max-age`: 3600 seconds (1 hour)

### Logout

#### `POST /auth/logout`

Logout and clear the authentication cookie.

**Request Body:**
```
(No body required)
```

**Response:**
```json
{
  "message": "Logout successful"
}
```

**Cookie Cleared:**
- `access_token`: Cookie is set to empty value with immediate expiration

### Using Authentication

**All API requests require authentication via httpOnly cookies:**

```javascript
// Include credentials to send cookies
fetch('/api/endpoint', {
  credentials: 'include'
});
```

### Protected Endpoints

**All endpoints require authentication except:**
- `POST /auth/login`
- `POST /auth/logout`

**User Ownership:**
- Users can only access/modify their own configs, simulations, and private templates
- Public agent/config templates are visible to all authenticated users
- Private templates are only visible to their owners

---

## System Architecture

### Embedding Service

The system uses a shared embedding service that is initialized once during application startup. This service provides text embeddings for similarity analysis, semantic matching, and analytical computations across all simulations.

**Key Features:**
- **Provider Abstraction**: Supports multiple embedding providers (HuggingFace, ONNX, OpenRouter)
- **Shared Architecture**: Single service instance used across all simulations and agents
- **Caching**: LRU cache with TTL for performance optimization
- **Thread-Safe**: Designed for concurrent access from multiple simulation threads

**Configuration:**
- Embedding provider and model are configured at startup via environment variables
- Default provider: ONNX with MiniLM model for optimal performance/resource balance
- Cannot be changed per simulation - all simulations use the same embedding service

**Environment Variables:**
- `EMBEDDING_PROVIDER`: Provider type (onnx, huggingface, openrouter)
- `EMBEDDING_MODEL`: Model name (default: sentence-transformers/all-MiniLM-L6-v2)
- `EMBEDDING_CACHE_SIZE`: Cache capacity (default: 1000)
- `EMBEDDING_CACHE_TTL`: Cache TTL in seconds (default: 3600)

---

## API Endpoints

### Health Check

#### `GET /healthz`

**Response:**
```json
{
  "ok": true
}
```

---

### Available Models

#### `GET /simulations/models`

Retrieves available models for agent configuration.

**Response:**
```json
{
  "models": [
    {
      "id": "openai/gpt-4o",
      "name": "GPT-4o",
      "description": "Most capable OpenAI model, excellent for complex reasoning",
      "provider": "openai"
    },
    {
      "id": "openai/gpt-4o-mini",
      "name": "GPT-4o Mini",
      "description": "Faster and cheaper version of GPT-4o",
      "provider": "openai"
    }
  ],
  "default_model": "openai/gpt-4o-mini"
}
```

---

#### `GET /simulations/tools`

Retrieves available tools for agent configuration.

**Response:**
```json
{
  "tools": {
    "web_search_tools": [
      {
        "id": "wikipedia_tool",
        "name": "Wikipedia",
        "description": "Search Wikipedia articles",
        "icon": "BookOpen",
        "config_schema": {
          "enabled": {"type": "boolean", "default": false, "description": "Enable Wikipedia search"},
          "canvas_position": {
            "type": "object",
            "properties": {
              "x": {"type": "number", "description": "X coordinate on canvas"},
              "y": {"type": "number", "description": "Y coordinate on canvas"}
            },
            "description": "Position of tool node on visual canvas"
          }
        }
      },
      {
        "id": "news_tool",
        "name": "News",
        "description": "Search news articles",
        "icon": "Newspaper",
        "config_schema": {
          "enabled": {"type": "boolean", "default": false, "description": "Enable news search"},
          "sources": {"type": "array", "items": {"type": "string"}, "default": [], "description": "News source domains to search"},
          "canvas_position": {
            "type": "object",
            "properties": {
              "x": {"type": "number", "description": "X coordinate on canvas"},
              "y": {"type": "number", "description": "Y coordinate on canvas"}
            },
            "description": "Position of tool node on visual canvas"
          }
        }
      },
      {
        "id": "pages_tool",
        "name": "Web Pages",
        "description": "Search general web pages",
        "icon": "Globe",
        "config_schema": {
          "enabled": {"type": "boolean", "default": false, "description": "Enable general web page search"},
          "sources": {"type": "array", "items": {"type": "string"}, "default": [], "description": "Web page domains to search"},
          "canvas_position": {
            "type": "object",
            "properties": {
              "x": {"type": "number", "description": "X coordinate on canvas"},
              "y": {"type": "number", "description": "Y coordinate on canvas"}
            },
            "description": "Position of tool node on visual canvas"
          }
        }
      },
      {
        "id": "google_ai_tool",
        "name": "Google AI",
        "description": "Enhanced search with AI summaries",
        "icon": "Sparkles",
        "config_schema": {
          "enabled": {"type": "boolean", "default": false, "description": "Enable Google AI enhanced search"},
          "canvas_position": {
            "type": "object",
            "properties": {
              "x": {"type": "number", "description": "X coordinate on canvas"},
              "y": {"type": "number", "description": "Y coordinate on canvas"}
            },
            "description": "Position of tool node on visual canvas"
          }
        }
      }
    ],
    "recall_tools": [
      {
        "id": "documents_tool",
        "name": "Document Recall",
        "description": "Recall from uploaded or preloaded documents",
        "icon": "FileText",
        "config_schema": {
          "enabled": {"type": "boolean", "default": false, "description": "Enable document recall (RAG)"},
          "canvas_position": {
            "type": "object",
            "properties": {
              "x": {"type": "number", "description": "X coordinate on canvas"},
              "y": {"type": "number", "description": "Y coordinate on canvas"}
            },
            "description": "Position of tool node on visual canvas"
          }
        }
      },
      {
        "id": "notes_tool",
        "name": "Notes Recall",
        "description": "Recall from debate interventions and tool usages (notes)",
        "icon": "StickyNote",
        "config_schema": {
          "enabled": {"type": "boolean", "default": false, "description": "Enable notes recall (RAG)"},
          "canvas_position": {
            "type": "object",
            "properties": {
              "x": {"type": "number", "description": "X coordinate on canvas"},
              "y": {"type": "number", "description": "Y coordinate on canvas"}
            },
            "description": "Position of tool node on visual canvas"
          }
        }
      }
    ]
  }
}
```

---

## Agent Templates

#### `GET /agents/templates`

Retrieves agent templates: public templates plus user's private templates.

Retrieves public agent templates.

**Query Parameters:**
- `limit` (integer, optional, default: 50, max: 100): Number of templates to return
- `offset` (integer, optional, default: 0): Number of templates to skip

**Response:**
```json
{
  "agents": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Centrist Economist",
      "description": "A moderate economist who focuses on balanced fiscal policy",
      "visibility": "public",
      "config": {
        "model": "openai/gpt-4o-mini",
        "lm_config": {
          "temperature": 0.7,
          "max_tokens": 500
        },
        "background": "You are a centrist economist...",
        "bias": 0.0,
        "personality_traits": ["analytical", "moderate"],
        "speaking_style": "professional and measured"
      },
      "created_at": "2025-09-01T12:00:00.000000",
      "updated_at": "2025-09-01T12:00:00.000000"
    }
  ],
  "total": 8
}
```

---

#### `GET /agents/templates/{agent_id}`

Retrieves a specific agent template by ID. Shows public templates or user's private templates.

**Path Parameters:**
- `agent_id` (string): UUID of the agent template

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Centrist Economist",
  "description": "A moderate economist who focuses on balanced fiscal policy",
  "visibility": "public",
  "config": {
    "model": "openai/gpt-4o-mini",
    "lm_config": {
      "temperature": 0.7,
      "max_tokens": 500
    },
    "background": "You are a centrist economist...",
    "bias": 0.0,
    "personality_traits": ["analytical", "moderate"],
    "speaking_style": "professional and measured"
  },
  "created_at": "2025-09-01T12:00:00.000000",
  "updated_at": "2025-09-01T12:00:00.000000"
}
```

**Error Responses:**
- `400`: Invalid agent ID format
- `404`: Agent template not found

---

## Config Templates

#### `GET /config-templates`

Retrieves config templates: public templates plus user's private templates. These are immutable blueprints that define debate parameters and agent configurations.

**Query Parameters:**
- `limit` (int, optional): Number of templates to return (1-100, default: 50)
- `offset` (int, optional): Number of templates to skip (default: 0)

**Response:**
```json
{
  "templates": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "Economic Policy Debate",
      "description": "A template for debates about economic policies with 3 agents",
      "visibility": "public",
      "parameters": {
        "max_iters": 21,
        "bias": [0.3, -0.1, 0.5],
        "stance": "Should minimum wage be increased?",
        "agent_count": 3
      },
      "created_at": "2025-09-03T10:30:00Z"
    }
  ],
  "total": 3
}
```

#### `GET /config-templates/{template_id}`

Retrieves a specific config template by ID. Shows public templates or user's private templates.

**Path Parameters:**
- `template_id` (string): UUID of the config template

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "Economic Policy Debate",
  "description": "A template for debates about economic policies with 3 agents",
  "visibility": "public",
  "parameters": {
    "max_iters": 21,
    "bias": [0.3, -0.1, 0.5],
    "stance": "Should minimum wage be increased?",
    "agent_count": 3
  },
  "agents": [
    {
      "position": 1,
      "name": "Conservative Economist",
      "profile": "You are a conservative economist...",
      "model_id": "openai/gpt-4o",
  "web_search_tools": {
      "recall_tools": {
        "documents_tool": {
          "enabled": true,
          "canvas_position": null
        },
        "notes_tool": {
          "enabled": true,
          "canvas_position": null
        }
      },
        "news_tool": null,
        "pages_tool": {
          "enabled": true,
          "sources": ["reuters.com", "bloomberg.com"],
          "canvas_position": null
        },
        "google_ai_tool": null,
        "wikipedia_tool": {
          "enabled": true,
          "sources": [],
          "canvas_position": null
        }
      },
      "canvas_position": null,
      "created_at": "2025-09-03T10:30:00Z"
    },
    {
      "position": 2,
      "name": "Progressive Activist",
      "profile": "You are a progressive activist...",
      "model_id": "openai/gpt-4o-mini",
      "web_search_tools": {
        "news_tool": {
          "enabled": true,
          "sources": ["theguardian.com", "cnn.com"],
          "canvas_position": null
        },
        "pages_tool": null,
        "google_ai_tool": null,
        "wikipedia_tool": {
          "enabled": true,
          "sources": [],
          "canvas_position": null
        }
      },
      "canvas_position": null,
      "created_at": "2025-09-03T10:30:00Z"
    }
  ],
  "created_at": "2025-09-03T10:30:00Z"
}
```

**Error Responses:**
- `400`: Invalid template ID format
- `404`: Config template not found

---

## Configs

Configs are editable debate configurations that contain parameters and associated agent snapshots. Unlike templates, configs can be modified and versioned over time.

**Data Structure Notes:**
- **Parameters**: Core debate settings (topic, max_iters, bias, etc.) stored in the `parameters` field
- **Agents**: Agent configurations with canvas positions stored separately in agent snapshot records
- **Agent Structure**: Each agent includes `profile`, `model_id`, `web_search_tools`, `recall_tools`, and `canvas_position` at the top level (no nested snapshot object)
- **Versioning**: Parameters changes increment version number, agent changes are tracked in snapshots

#### `GET /configs`

Retrieves configs for the authenticated user. These are editable instances that can be modified and used as starting points for debates.

**Query Parameters:**
- `limit` (int, optional): Number of configs to return (1-100, default: 50)
- `offset` (int, optional): Number of configs to skip (default: 0)

**Response:**
```json
{
  "configs": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "name": "Modified Economic Debate",
      "description": "A modified version of the economic policy debate template",
      "visibility": "public",
      "parameters": {
        "max_iters": 15,
        "bias": [0.2, -0.2, 0.4],
        "stance": "Should minimum wage be increased to $20/hour?",
        "agent_count": 3
      },
      "version_number": 2,
      "source_template_id": "550e8400-e29b-41d4-a716-446655440001",
      "created_at": "2025-09-03T10:30:00Z",
      "updated_at": "2025-09-03T11:15:00Z"
    }
  ],
  "total": 7
}
```

#### `POST /configs`

Creates a new blank config with default values. This is used by the frontend editor which requires a config ID to operate.

**Request Body:**
```json
{}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440005",
  "name": "Untitled Config",
  "description": null,
  "visibility": "private",
  "parameters": {
    "topic": "Should artificial intelligence development be regulated by government?",
    "max_iters": 21,
    "bias": [],
    "stance": "",
  },
  "version_number": 1,
  "agents": [],
  "source_template_id": null,
  "created_at": "2025-09-03T12:00:00Z",
  "updated_at": "2025-09-03T12:00:00Z"
}
```

#### `PATCH /configs/{config_id}`

Updates a config with new values. Only provided fields are updated. Increments version number if debate parameters change.

**Path Parameters:**
- `config_id` (string): UUID of the config to update

**Request Body (all fields optional):**
```json
{
  "name": "Updated Economic Debate",
  "description": "Modified description",
  "topic": "Should minimum wage be $25/hour?",
  "agents": [
    {
      "name": "Progressive Economist",
      "profile": "You strongly support higher wages",
      "model_id": "openai/gpt-4o",
      "lm_config": {
        "temperature": 0.7,
        "max_tokens": 600
      },
  "web_search_tools": {
      "recall_tools": {
        "documents_tool": {
          "enabled": true,
          "canvas_position": null
        },
        "notes_tool": {
          "enabled": false,
          "canvas_position": null
        }
      },
        "wikipedia_tool": {
          "enabled": true,
          "canvas_position": {
            "x": 100,
            "y": 200
          }
        },
        "news_tool": {
          "enabled": true,
          "sources": ["reuters.com", "bbc.com"],
          "canvas_position": {
            "x": 200,
            "y": 250
          }
        }
      },
      "canvas_position": {
        "x": 50,
        "y": 100
      }
    }
  ],
  "max_iters": 15,
  "bias": [0.5, -0.3],
  "stance": "pro-increase",
  "max_interventions_per_agent": 2
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440005",
  "name": "Updated Economic Debate",
  "description": "Modified description",
  "visibility": "private",
  "parameters": {
    "topic": "Should minimum wage be $25/hour?",
    "max_iters": 15,
    "bias": [0.5, -0.3],
    "stance": "pro-increase"
  },
  "version_number": 2,
  "agents": [...],
  "source_template_id": null,
  "created_at": "2025-09-03T12:00:00Z",
  "updated_at": "2025-09-03T12:05:00Z"
}
```

**Important Notes:**
- **Agent Data Storage**: Agents are stored separately from config parameters. Agent data (including canvas positions and web search tools) is stored in dedicated agent snapshot records, not in the `parameters` field.
- **Canvas Positioning**: Each agent can have optional `canvas_position` with `x` and `y` coordinates for UI layout.
- **Agent Config Consistency**: The `agents` array must use the same `AgentConfig` structure as in `POST /simulations`, including complete `web_search_tools` and `recall_tools` configuration when applicable.

**Versioning Behavior:**
- If only `name` or `description` change → version stays same
- If any debate parameters change → version increments
- `updated_at` timestamp always updates

**Error Responses:**
- `400`: Invalid config ID format
- `404`: Config not found

#### `GET /configs/{config_id}`

Retrieves a specific public config by ID.

**Path Parameters:**
- `config_id` (string): UUID of the config

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "name": "Modified Economic Debate",
  "description": "A modified version of the economic policy debate template",
  "visibility": "public",
  "parameters": {
    "max_iters": 15,
    "bias": [0.2, -0.2, 0.4],
    "stance": "Should minimum wage be increased to $20/hour?",
    "agent_count": 3
  },
  "version_number": 2,
  "source_template_id": "550e8400-e29b-41d4-a716-446655440001",
  "agents": [
    {
      "position": 1,
      "name": "Conservative Economist",
      "profile": "You are a conservative economist...",
      "model_id": "openai/gpt-4o",
      "web_search_tools": {
        "news_tool": null,
        "pages_tool": {
          "enabled": true,
          "sources": ["reuters.com", "bloomberg.com"],
          "canvas_position": null
        },
        "google_ai_tool": null,
        "wikipedia_tool": {
          "enabled": true,
          "sources": [],
          "canvas_position": null
        }
      },
      "canvas_position": {
        "x": 100.5,
        "y": 200.0
      },
      "created_at": "2025-09-03T10:30:00Z"
    },
    {
      "position": 2,
      "name": "Progressive Activist",
      "profile": "You are a progressive activist...",
      "model_id": "openai/gpt-4o-mini",
      "web_search_tools": {
        "news_tool": {
          "enabled": true,
          "sources": ["theguardian.com", "cnn.com"],
          "canvas_position": null
        },
        "pages_tool": null,
        "google_ai_tool": null,
        "wikipedia_tool": {
          "enabled": true,
          "sources": [],
          "canvas_position": null
        }
      },
      "canvas_position": {
        "x": 300.0,
        "y": 150.75
      },
      "created_at": "2025-09-03T10:30:00Z"
    }
  ],
  "created_at": "2025-09-03T10:30:00Z",
  "updated_at": "2025-09-03T11:15:00Z"
}
```

#### `GET /configs/{config_id}/runs`

Retrieves all simulation runs for a specific config, regardless of which version was used.

**Path Parameters:**
- `config_id` (string): UUID of the config

**Query Parameters:**
- `limit` (int, optional): Number of runs to return (1-100, default: 50)
- `offset` (int, optional): Number of runs to skip (default: 0)

**Response:**
```json
{
  "runs": [
    {
      "simulation_id": "550e8400-e29b-41d4-a716-446655440003",
      "config_id": "550e8400-e29b-41d4-a716-446655440002",
      "config_name": "Modified Economic Debate",
      "config_version_when_run": 1,
      "is_latest_version": false,
      "status": "finished",
      "is_finished": true,
      "created_at": "2025-09-03T10:00:00Z",
      "finished_at": "2025-09-03T10:15:00Z"
    },
    {
      "simulation_id": "550e8400-e29b-41d4-a716-446655440004",
      "config_id": "550e8400-e29b-41d4-a716-446655440002",
      "config_name": "Modified Economic Debate",
      "config_version_when_run": 2,
      "is_latest_version": true,
      "status": "running",
      "is_finished": false,
      "created_at": "2025-09-03T11:00:00Z",
      "finished_at": null
    }
  ],
  "total": 2
}
```

**Error Responses:**
- `400`: Invalid config ID format
- `404`: Config not found

---

#### `DELETE /configs/{config_id}`

Permanently deletes a config and all related entities including runs, events, summaries, analytics, versions, and agent snapshots.

**Path Parameters:**
- `config_id` (string): UUID of the config to delete

**Response:**
```json
{
  "message": "Config 'Economic Policy Debate' and all related data deleted successfully",
  "deleted_config_id": "550e8400-e29b-41d4-a716-446655440002",
  "deleted_runs_count": 3
}
```

**What Gets Deleted:**
- **Config**: The main config record
- **Config Versions**: All historical versions of the config
- **Config Agents**: All agent snapshots associated with the config
- **Runs**: All simulation runs created from this config
- **Run Events**: All debate events from associated runs
- **Summaries**: All voting summaries from associated runs
- **Run Analytics**: All cached analytics data from associated runs

**Warning**: This operation is **irreversible**. All simulation data, results, and analytics for runs created from this config will be permanently lost.

**Error Responses:**
- `400`: Invalid config ID format
- `404`: Config not found
- `500`: Database error during deletion

**Use Cases:**
- Clean up test/development configs
- Remove configs that are no longer needed
- Free up database space by removing obsolete simulation data

---

## Config Snapshots

Config snapshots provide access to historical versions of configs, preserving the complete state (parameters + agents) at each version. This enables viewing and "collapsing" past config versions into new editable configs.

**Agent Snapshot Contents:**
- **Profile**: The agent's personality and behavioral instructions
- **Model ID**: The language model assigned to the agent
- **Web Search Tools**: Complete configuration of all search tools (news_tool, pages_tool, google_ai_tool, wikipedia_tool)
- **Canvas Position**: Position coordinates for both the agent and individual tools on the visual canvas

#### `GET /config-versions/{config_id}/versions/{version_number}`

Retrieves a specific config version by config ID and version number. Returns the complete config state as it existed at that version, including all agents and their configurations.

**Path Parameters:**
- `config_id` (string): UUID of the config
- `version_number` (integer): Version number to retrieve

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "name": "Modified Economic Debate (v2)",
  "description": "A modified version of the economic policy debate template",
  "parameters": {
    "topic": "Should minimum wage be increased to $20/hour?",
    "max_iters": 15,
    "bias": [0.2, -0.2, 0.4],
    "stance": "neutral"
  },
  "version_number": 2,
  "agents": [
    {
      "position": 1,
      "name": "Conservative Economist",
      "profile": "You are a conservative economist concerned about fiscal policy...",
      "model_id": "openai/gpt-4o",
      "web_search_tools": {
        "news_tool": null,
        "pages_tool": {
          "enabled": true,
          "sources": ["reuters.com", "bloomberg.com"],
          "canvas_position": null
        },
        "google_ai_tool": null,
        "wikipedia_tool": {
          "enabled": true,
          "sources": [],
          "canvas_position": null
        }
      },
      "canvas_position": {
        "x": 100.5,
        "y": 200.0
      },
      "created_at": "2025-09-24T00:00:00Z"
    },
    {
      "position": 2,
      "name": "Progressive Activist",
      "profile": "You are a progressive activist focused on workers' rights...",
      "model_id": "anthropic/claude-3.5-sonnet",
      "web_search_tools": {
        "news_tool": {
          "enabled": true,
          "sources": ["theguardian.com", "cnn.com"],
          "canvas_position": null
        },
        "pages_tool": null,
        "google_ai_tool": null,
        "wikipedia_tool": {
          "enabled": true,
          "sources": [],
          "canvas_position": null
        }
      },
      "canvas_position": {
        "x": 300.0,
        "y": 150.75
      },
      "created_at": "2025-09-24T00:00:00Z"
    }
  ],
  "source_template_id": "550e8400-e29b-41d4-a716-446655440001",
  "created_at": "2025-09-24T00:00:00Z",
  "updated_at": "2025-09-24T00:00:00Z"
}
```

**Key Features:**
- **Complete historical state**: Includes both parameters and agents as they existed at that version
- **Canvas positions**: Preserves agent positions on the frontend canvas (stored as floats)
- **Immutable versions**: Historical versions cannot be modified
- **Version indication**: Config name includes version number for clarity

**Use Cases:**
- **Version comparison**: Compare different versions of the same config
- **Historical analysis**: Review how configs evolved over time
- **Config restoration**: "Collapse" old versions into new editable configs
- **Audit trail**: Track what configuration was used for specific simulation runs

**Error Responses:**
- `400`: Invalid config ID format
- `404`: Config not found
- `404`: Version not found for specified version

**Notes:**
- Versions are automatically created when configs are saved or used in simulations
- Only configs that have been saved or used in simulations will have versions
- Version numbers start from 1 and increment with each parameter change

---

## Documents

The document library system allows users to upload and manage documents that can be used by agents during debates through the document recall tool. Documents are processed, chunked, and embedded for efficient retrieval.

#### `GET /documents`

Retrieves the user's document library with pagination.

**Query Parameters:**
- `limit` (int, optional): Number of documents to return (1-100, default: 50)
- `offset` (int, optional): Number of documents to skip (default: 0)

**Response:**
```json
{
  "documents": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Economic Policy Research Paper",
      "description": "Analysis of minimum wage impacts",
      "document_type": "research_paper",
      "original_filename": "econ_research.pdf",
      "file_size": 245760,
      "mime_type": "application/pdf",
      "processing_status": "completed",
      "embedding_status": "completed",
      "error_message": null,
      "tags": ["economics", "policy", "research"],
      "created_at": "2025-10-31T10:30:00Z",
      "updated_at": "2025-10-31T10:35:00Z"
    }
  ],
  "total": 1
}
```

#### `POST /documents`

Uploads a new document to the user's library. The document will be processed to extract text content and generate embeddings for retrieval.

**Content-Type:** `multipart/form-data`

**Form Parameters:**
- `file` (file, required): The document file to upload
- `title` (string, required): Document title
- `description` (string, optional): Document description
- `document_type` (string, optional): Type of document (default: "general")
- `tags` (string, optional): Comma-separated tags

**Supported File Types:**
- `text/plain` - Plain text files
- `text/markdown` - Markdown files
- `application/pdf` - PDF documents
- `application/msword` - Microsoft Word documents (.doc)
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` - Microsoft Word documents (.docx)

**File Size Limit:** 10MB

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Economic Policy Research Paper",
  "processing_status": "completed",
  "embedding_status": "pending",
  "message": "Document uploaded successfully"
}
```

#### `GET /documents/{document_id}`

Retrieves a specific document from the user's library, including full content.

**Path Parameters:**
- `document_id` (string): UUID of the document

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Economic Policy Research Paper",
  "description": "Analysis of minimum wage impacts",
  "document_type": "research_paper",
  "original_filename": "econ_research.pdf",
  "file_size": 245760,
  "mime_type": "application/pdf",
  "processing_status": "completed",
  "embedding_status": "completed",
  "error_message": null,
  "tags": ["economics", "policy", "research"],
  "content": "Full text content of the document...",
  "created_at": "2025-10-31T10:30:00Z",
  "updated_at": "2025-10-31T10:35:00Z"
}
```

#### `DELETE /documents/{document_id}`

Deletes a document from the user's library along with all associated embeddings.

**Path Parameters:**
- `document_id` (string): UUID of the document

**Response:**
```json
{
  "message": "Document deleted successfully"
}
```

#### `GET /documents/{document_id}/status`

Retrieves the processing status of a specific document.

**Path Parameters:**
- `document_id` (string): UUID of the document

**Response:**
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "processing_status": "completed",
  "embedding_status": "completed",
  "error_message": null
}
```

**Document Processing States:**
- `processing_status`: 
  - `pending`: Document uploaded but not yet processed
  - `processing`: Currently extracting text content
  - `completed`: Text extraction completed successfully
  - `failed`: Text extraction failed
- `embedding_status`:
  - `pending`: Waiting for embedding generation
  - `processing`: Currently generating embeddings
  - `completed`: Embeddings generated successfully
  - `failed`: Embedding generation failed

**Document Integration with Debates:**
- Documents are private to each user
- Can be assigned to agents during debate setup via the documents tool
- Agents can recall information from assigned documents using the document recall tool
- Document chunks are embedded and searchable during debates

---

## Simulation Management

#### `POST /simulations`

Creates and starts a new debate simulation.

**Request Body:**
```json
{
  "config_id": "550e8400-e29b-41d4-a716-446655440000",
  "config_name": "My Economic Debate",
  "config_description": "A debate about economic policies",
  "topic": "Should minimum wage be raised to $20/hour?",
  "agents": [
    {
      "name": "TechExec", 
      "profile": "You are a tech executive concerned about business costs",
      "model_id": "openai/gpt-4o",
      "lm_config": {
        "temperature": 0.3,
        "max_tokens": 800,
        "top_p": 0.9
      }
    },
    {
      "name": "PrivacyAdvocate", 
      "profile": "You are a privacy rights advocate",
      "model_id": "anthropic/claude-3.5-sonnet",
      "lm_config": {
        "temperature": 0.7,
        "max_tokens": 600
      }
    }
  ],
  "max_iters": 21,
  "bias": [0.1, 0.2],
  "stance": "pro-regulation",
  "max_interventions_per_agent": 3
}
```

**Required Fields:**
- `topic` (string): The debate topic
- `agents` (array): Agent configurations
  - `name` (string): Agent name
  - `profile` (string): Background description
  - `model_id` (string, optional): Language model ID
  - `lm_config` (object, optional): Language model parameters
    - `temperature` (float, 0.0-2.0): Controls response creativity/randomness
    - `max_tokens` (integer, 1-4096): Maximum response length
    - `top_p` (float, 0.0-1.0): Nucleus sampling parameter
    - `frequency_penalty` (float, -2.0-2.0): Reduces repetition (OpenAI models only)
    - `presence_penalty` (float, -2.0-2.0): Encourages new topics (OpenAI models only)
  - `web_search_tools` (object, optional): Web search tools configuration
    - `wikipedia_tool` (object, optional): Wikipedia tool configuration
      - `enabled` (boolean, default: false): Enable Wikipedia content extraction
      - `canvas_position` (object, optional): Position of tool node on visual canvas
        - `x` (float): X coordinate
        - `y` (float): Y coordinate
    - `news_tool` (object, optional): News tool configuration
      - `enabled` (boolean, default: false): Enable news source content extraction
      - `sources` (array of strings, default: []): News domain sources (e.g., ["bbc.com", "reuters.com"])
      - `canvas_position` (object, optional): Position of tool node on visual canvas
        - `x` (float): X coordinate
        - `y` (float): Y coordinate
    - `pages_tool` (object, optional): Pages tool configuration
      - `enabled` (boolean, default: false): Enable generic web page content extraction
      - `sources` (array of strings, default: []): Specific page domains (e.g., ["example.com", "site.org"])
      - `canvas_position` (object, optional): Position of tool node on visual canvas
        - `x` (float): X coordinate
        - `y` (float): Y coordinate
    - `google_ai_tool` (object, optional): Google AI tool configuration
      - `enabled` (boolean, default: false): Enable Google AI search via SerpAPI
      - `canvas_position` (object, optional): Position of tool node on visual canvas
        - `x` (float): X coordinate
        - `y` (float): Y coordinate
  - `recall_tools` (object, optional): Recall tools configuration
    - `documents_tool` (object, optional): Document recall tool configuration
      - `enabled` (boolean, default: false): Enable document recall (RAG)
      - `canvas_position` (object, optional): Position of tool node on visual canvas
        - `x` (float): X coordinate
        - `y` (float): Y coordinate
    - `notes_tool` (object, optional): Notes recall tool configuration
      - `enabled` (boolean, default: false): Enable notes recall (RAG)
      - `canvas_position` (object, optional): Position of tool node on visual canvas
        - `x` (float): X coordinate
        - `y` (float): Y coordinate
  - `canvas_position` (object, optional): Position on the visual canvas
    - `x` (float): X coordinate
    - `y` (float): Y coordinate


**Web Search Tools:**
The web search tools use a complementary approach with Google Custom Search Engine (PSE) as baseline and Google AI as enhancement. When enabled, agents can automatically search for information using DSPy's ReAct module:
- **PSE (Primary Search Engine)**: Uses Google Custom Search with service account authentication
- **Google AI**: Enhanced search via SerpAPI (requires SERPAPI_API_KEY environment variable)
- **Content Extraction**: Configurable extractors for Wikipedia, news sources, and specific web pages
- **Tool Integration**: Agents automatically decide when and how to use the search tools during conversations
- **Canvas Positioning**: Each tool can have an optional `canvas_position` field for UI layout. If a tool is not enabled or has no position data, the frontend can determine appropriate positioning.

**Recall Tools:**
The recall tools provide agents with RAG (Retrieval-Augmented Generation) capabilities:
- **documents_tool**: Allows agents to recall information from uploaded or preloaded documents (private to each agent)
- **notes_tool**: Allows agents to recall from their own interventions and tool usages (notes)
- **Frontend Handling**: The frontend should treat `documents_tool` and `notes_tool` as two separate tools, just like the web search tools. Each can be enabled/disabled and positioned independently.
- **Tool Integration**: Agents can use recall tools to retrieve citeable, reliable information from their own debate history or uploaded documents, with no summarization step.
- **Canvas Positioning**: Each recall tool can have an optional `canvas_position` field for UI layout.

**Important: Agent Config Consistency**
The `AgentConfig` structure (including both `web_search_tools` and `recall_tools`) must be identical between:
- **POST /simulations** (this endpoint)
- **PATCH /configs/{config_id}** (config updates)

Both endpoints expect the complete `AgentConfig` object with all fields, including both `web_search_tools` and `recall_tools`. When running a simulation from a saved config, ensure the frontend sends the complete agent configuration including any configured tools, not just basic fields like name and profile.

**LM Config Provider Compatibility:**
- **OpenAI models** (`openai/*`): All parameters supported
- **Anthropic models** (`anthropic/*`): temperature, max_tokens, top_p
- **Google models** (`google/*`): temperature, max_tokens  
- **Meta models** (`meta-llama/*`): temperature, max_tokens, top_p
- Unsupported parameters are automatically filtered out based on the model provider

**Optional Fields:**
- `config_id` (string): Existing config ID to auto-save changes to
- `config_name` (string, default: "Untitled Simulation"): Name for auto-saved config
- `config_description` (string): Description for auto-saved config
- `max_iters` (integer, default: 21): Maximum iterations
- `bias` (array of floats): Bias weights for each agent
- `stance` (string): Initial stance
- `max_interventions_per_agent` (integer, optional): Maximum number of times each agent can speak during the debate. If not provided, agents can speak unlimited times (subject to other stopping conditions)

**Auto-Save Behavior:**
- If `config_id` is provided, the backend will check if the simulation parameters differ from the stored config
- If different, it automatically creates a new version of the config and increments the version number
- This allows tracking which version of a config was used for each simulation run

**Example Request with Tools Configuration:**
```json
{
  "agents": [
    {
      "name": "TechAnalyst",
      "profile": "A technology analyst specialized in AI and emerging tech trends",
      "model_id": "openai/gpt-4",
      "lm_config": {
        "temperature": 0.7,
        "max_tokens": 1000
      },
      "web_search_tools": {
        "google_ai_tool": {
          "enabled": true,
          "canvas_position": { "x": 150.5, "y": 200.0 }
        },
        "wikipedia_tool": {
          "enabled": true,
          "canvas_position": { "x": 250.0, "y": 150.75 }
        },
        "news_tool": {
          "enabled": true,
          "sources": ["techcrunch.com", "wired.com", "arstechnica.com"],
          "canvas_position": { "x": 350.25, "y": 180.5 }
        },
        "pages_tool": {
          "enabled": true,
          "sources": ["github.com", "arxiv.org"],
          "canvas_position": { "x": 450.0, "y": 220.25 }
        }
      },
      "recall_tools": {
        "documents_tool": {
          "enabled": true,
          "canvas_position": { "x": 500.0, "y": 250.0 }
        },
        "notes_tool": {
          "enabled": false,
          "canvas_position": null
        }
      }
    },
    {
      "name": "PolicyExpert",
      "profile": "A policy expert focused on technology regulation",
      "model_id": "anthropic/claude-3-sonnet",
      "web_search_tools": {
        "wikipedia_tool": {
          "enabled": true,
          "canvas_position": { "x": 300.0, "y": 100.0 }
        },
        "news_tool": {
          "enabled": true,
          "sources": ["reuters.com", "bbc.com", "politico.com"],
          "canvas_position": { "x": 400.75, "y": 125.5 }
        }
      },
      "recall_tools": {
        "documents_tool": {
          "enabled": false,
          "canvas_position": null
        },
        "notes_tool": {
          "enabled": true,
          "canvas_position": { "x": 600.0, "y": 300.0 }
        }
      }
    }
  ],
  "topic": "The impact of AI regulation on innovation",
  "max_iters": 15,
  "config_name": "AI Regulation Debate with Tools"
}
```

**Response:**
```json
{
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "created",
  "message": "Simulation started, use GET /simulations/{id} to check progress"
}
```

---

#### `GET /simulations/{sim_id}`

Retrieves simulation status and progress.

**Path Parameters:**
- `sim_id` (string): Simulation ID

**Response:**
```json
{
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "config_id": "550e8400-e29b-41d4-a716-446655440001",
  "config_name": "My Economic Debate",
  "config_version_when_run": 2,
  "is_latest_version": true,
  "status": "running",
  "progress": {
    "current_iteration": 5,
    "max_iterations": 21,
    "percentage": 23.8
  },
  "latest_events": [
    {
      "iteration": 4,
      "speaker": "TechExec",
      "opinion": "I believe that excessive regulation could stifle innovation...",
      "engaged": ["PrivacyAdvocate"],
      "finished": false,
      "timestamp": "2025-08-30T01:05:04.072115",
      "reasoning_steps": [
        "I need to consider the economic implications of regulation...",
        "Let me research recent examples of regulatory impact on tech..."
      ],
      "prediction_metadata": {
        "counter_target": "The idea that regulation always benefits consumers",
        "counter_type": "rebuttal",
        "tone": "analytical",
        "stance_strength": "0.8",
        "novelty_estimate": "0.6",
        "persona_fit_estimate": "0.9",
        "references_used": "Economic studies on tech regulation"
      },
      "reasoning_timeline": [
        {
          "type": "thought",
          "step": 0,
          "content": "I need to consider the economic implications of regulation..."
        },
        {
          "type": "tool_call",
          "step": 0,
          "tool_name": "web_search_agent_0",
          "query": "recent tech regulation economic impact studies",
          "result": "Recent studies show mixed results on regulation impact..."
        },
        {
          "type": "thought", 
          "step": 1,
          "content": "The search yielded useful data, now I can formulate my response..."
        }
      ],
      "tool_usages": [
        {
          "id": "tool-uuid-123",
          "tool_name": "web_search_agent_0",
          "query": "recent tech regulation economic impact studies",
          "output": "Recent studies show mixed results on regulation impact...",
          "execution_time": 2.3,
          "created_at": "2025-08-30T01:05:02.150000"
        }
      ]
    }
  ],
  "is_finished": false,
  "stopped_reason": null,
  "started_at": "2025-08-30T01:04:55.123456",
  "finished_at": null,
  "created_at": "2025-08-30T01:04:54.987654"
}
```

**Enhanced Fields in `latest_events`:**
Each event in `latest_events` now includes rich debugging and analysis data:

- **Core Fields** (existing):
  - `iteration`, `speaker`, `opinion`, `engaged`, `finished`, `timestamp`

- **Reasoning & Analysis** (new):
  - `reasoning_steps` (array): Internal thought process steps from the agent
  - `reasoning_timeline` (array): **NEW** - Unified timeline showing interleaved thoughts and tool calls in order
    - Each item has `type` ('thought' or 'tool_call'), `step` (sequence number), and `content`/tool details
    - Preserves the exact order: thought → tool → observation → thought → tool → etc.
  - `prediction_metadata` (object): DSPy prediction metadata including:
    - `counter_target`: What the agent is responding to
    - `counter_type`: Type of response ('rebuttal', 'support', etc.)
    - `tone`: Emotional tone ('analytical', 'passionate', etc.)
    - `stance_strength`: How strongly the agent feels (0-1)
    - `novelty_estimate`: How original the response is (0-1)
    - `persona_fit_estimate`: How well it fits the agent's character (0-1)
    - `references_used`: Sources or citations mentioned

- **Tool Usage** (new):
  - `tool_usages` (array): All tools used during this intervention
    - `id`: Unique tool usage ID
    - `tool_name`: Name of the tool used
    - `query`: What the agent searched/asked for
    - `output`: Summary result from the tool
    - `execution_time`: How long the tool took (seconds)
    - `created_at`: When the tool was executed

**Configuration Fields:**
- `config_id` (string, nullable): ID of the config this run is associated with
- `config_name` (string, nullable): Name of the config for easy identification
- `config_version_when_run` (integer, nullable): Version number when this run was created
- `is_latest_version` (boolean, nullable): True if this run used the latest version of the config

**Status Values:**
- `"created"`: Just created, starting
- `"running"`: Actively running
- `"finished"`: Completed successfully
- `"failed"`: Encountered an error
- `"stopped"`: Manually stopped

**Stopped Reason Values:**
- `"Maximum iterations limit reached"`: Maximum iterations limit reached
- `"Agent opinions have converged too much"`: Agent opinions have converged too much
- `"No agents want to continue the debate"`: No agents want to speak further
- `"All agents have reached their maximum intervention limit"`: All agents have reached their maximum intervention limit
- `"Manually stopped by user"`: Manually stopped by user

---

#### `POST /simulations/{sim_id}/stop`

Stops a running simulation.

**Path Parameters:**
- `sim_id` (string): Simulation ID

**Response:**
```json
{
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "stopped",
  "message": "Stop request submitted"
}
```

---

#### `POST /simulations/{sim_id}/vote`

Triggers voting for a completed simulation. Each agent votes on the debate topic based on their final opinion and reasoning. Individual votes are stored with full agent context and can be retrieved on subsequent calls.

**Path Parameters:**
- `sim_id` (string): Simulation ID

**Response:**
```json
{
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "yea": 2,
  "nay": 1,
  "individual_votes": [
    {
      "agent_name": "TechExec",
      "agent_background": "Tech industry executive with focus on innovation and market growth",
      "vote": false,
      "reasoning": "While I support innovation, some basic safety regulations are necessary to prevent market failures"
    },
    {
      "agent_name": "PrivacyAdvocate", 
      "agent_background": "Digital rights activist focused on privacy protection",
      "vote": true,
      "reasoning": "Strong regulations are essential to protect citizen privacy and prevent corporate overreach"
    }
  ],
  "created_at": "2024-01-15T11:45:00Z"
}
```

**Features:**
- **Individual Vote Details**: Each agent's vote with essential context and reasoning
- **Simplified Response**: Only includes relevant voting information (name, background, vote, reasoning)
- **Idempotent**: Calling multiple times returns the same results (votes are stored permanently)
- **Rich Reasoning**: Each agent provides detailed explanation for their vote decision

**Requirements:**
- Simulation must have `status: "finished"`

**Response Fields:**
- `simulation_id`: UUID of the simulation
- `yea`: Total number of affirmative votes
- `nay`: Total number of negative votes  
- `individual_votes`: Array of individual vote objects containing:
  - `agent_name`: Name of the agent who voted
  - `agent_background`: Agent's stance/profile for context
  - `vote`: Boolean (true = yea, false = nay)
  - `reasoning`: Agent's explanation for their vote decision
- `created_at`: Timestamp when voting was completed

---

#### `GET /simulations/{sim_id}/votes`

Checks if votes exist for a simulation without triggering voting. Returns existing vote data in the same format as the voting endpoint, but only if votes have already been created.

**Path Parameters:**
- `sim_id` (string): Simulation ID

**Response:**
```json
{
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "yea": 2,
  "nay": 1,
  "individual_votes": [
    {
      "agent_name": "TechExec",
      "agent_background": "Tech industry executive with focus on innovation and market growth",
      "vote": false,
      "reasoning": "While I support innovation, some basic safety regulations are necessary to prevent market failures"
    },
    {
      "agent_name": "PrivacyAdvocate", 
      "agent_background": "Digital rights activist focused on privacy protection",
      "vote": true,
      "reasoning": "Strong regulations are essential to protect citizen privacy and prevent corporate overreach"
    }
  ],
  "created_at": "2024-01-15T11:45:00Z"
}
```

**Features:**
- **Read-only**: Does not trigger voting or modify any data
- **Same Format**: Returns identical response format as `POST /simulations/{sim_id}/vote`
- **Existence Check**: Only returns data if votes already exist

**Error Responses:**
- `400`: Invalid simulation ID format
- `404`: Simulation not found
- `404`: No votes found for this simulation

**Use Cases:**
- Check if voting has been completed without accidentally triggering new votes
- Retrieve existing vote results for display/analysis
- Validate vote existence before performing operations that depend on votes

---

#### `POST /simulations/{sim_id}/analyze`

Computes analytics for a completed simulation. Analytics include engagement matrices, participation statistics, and opinion similarity data. Results are cached for subsequent requests.

**Path Parameters:**
- `sim_id` (string): Simulation ID

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "computed_at": "2025-09-26T10:30:00",
  "analytics": [
    {
      "type": "engagement_matrix",
      "title": "Agent Engagement Matrix",
      "description": "Shows agent activity patterns across debate turns",
      "data": [
        [2, 0, 1, 0, 1],
        [1, 2, 0, 1, 0],
        [0, 1, 2, 1, 1]
      ],
      "metadata": {
        "agent_names": ["Sarah Mitchell", "James Thompson", "Maria Lopez"],
        "turn_count": 5,
        "legend": {
          "0": "inactive",
          "1": "engaged",
          "2": "speaking"
        }
      }
    },
    {
      "type": "participation_stats",
      "title": "Participation Statistics",
      "description": "Agent intervention counts, engagement rates, and participation percentages",
      "data": {
        "total_interventions": {
          "Sarah Mitchell": 2,
          "James Thompson": 2,
          "Maria Lopez": 1
        },
        "total_engagements": {
          "Sarah Mitchell": 3,
          "James Thompson": 2,
          "Maria Lopez": 4
        },
        "engagement_rates": {
          "Sarah Mitchell": 0.6,
          "James Thompson": 0.4,
          "Maria Lopez": 0.8
        },
        "participation_percentages": {
          "Sarah Mitchell": 40.0,
          "James Thompson": 40.0,
          "Maria Lopez": 20.0
        },
        "total_turns": 5
      },
      "metadata": {
        "agent_names": ["Sarah Mitchell", "James Thompson", "Maria Lopez"]
      }
    },
    {
      "type": "opinion_similarity",
      "title": "Opinion Similarity Matrix",
      "description": "Semantic similarity between agents' final opinions",
      "data": {
        "matrix": [
          [1.0, 0.23],
          [0.23, 1.0]
        ],
        "similarity_pairs": {
          "Sarah Mitchell_vs_Sarah Mitchell": 1.0,
          "Sarah Mitchell_vs_James Thompson": 0.23,
          "James Thompson_vs_Sarah Mitchell": 0.23,
          "James Thompson_vs_James Thompson": 1.0
        }
      },
      "metadata": {
        "speaking_agents": ["Sarah Mitchell", "James Thompson"],
        "similarity_range": {"min": 0.0, "max": 1.0},
        "note": "Higher values indicate more similar opinions. Only agents who spoke are included."
      }
    }
  ]
}
```

**Features:**
- **Idempotent**: Calling multiple times returns the same cached results
- **Comprehensive Analytics**: Includes engagement patterns, participation stats, and opinion similarity
- **Performance Optimized**: Results are cached in database after first computation

**Requirements:**
- Simulation must have `status: "finished"`

**Response Fields:**
- `run_id`: UUID of the simulation run
- `computed_at`: Timestamp when analytics were computed
- `analytics`: Array of individual analytics objects, each containing:
  - `type`: Analytics type identifier (e.g., "engagement_matrix", "participation_stats", "opinion_similarity")
  - `title`: Human-readable title for the analytics
  - `description`: Description of what the analytics show
  - `data`: The actual analytics data (format varies by type)
  - `metadata`: Additional context and configuration for rendering the analytics

---

#### `GET /simulations/{sim_id}/analytics`

Checks if analytics exist for a simulation without triggering computation. Returns existing analytics data in the same format as the analyze endpoint, but only if analytics have already been computed.

**Path Parameters:**
- `sim_id` (string): Simulation ID

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "computed_at": "2025-09-26T10:30:00",
  "analytics": [
    {
      "type": "engagement_matrix",
      "title": "Agent Engagement Matrix",
      "description": "Shows agent activity patterns across debate turns",
      "data": [
        [2, 0, 1, 0, 1],
        [1, 2, 0, 1, 0],
        [0, 1, 2, 1, 1]
      ],
      "metadata": {
        "agent_names": ["Sarah Mitchell", "James Thompson", "Maria Lopez"],
        "turn_count": 5,
        "legend": {
          "0": "inactive",
          "1": "engaged",
          "2": "speaking"
        }
      }
    },
    {
      "type": "participation_stats",
      "title": "Participation Statistics",
      "description": "Agent intervention counts, engagement rates, and participation percentages",
      "data": {
        "total_interventions": {
          "Sarah Mitchell": 2,
          "James Thompson": 2,
          "Maria Lopez": 1
        },
        "total_engagements": {
          "Sarah Mitchell": 3,
          "James Thompson": 2,
          "Maria Lopez": 4
        },
        "engagement_rates": {
          "Sarah Mitchell": 0.6,
          "James Thompson": 0.4,
          "Maria Lopez": 0.8
        },
        "participation_percentages": {
          "Sarah Mitchell": 40.0,
          "James Thompson": 40.0,
          "Maria Lopez": 20.0
        },
        "total_turns": 5
      },
      "metadata": {
        "agent_names": ["Sarah Mitchell", "James Thompson", "Maria Lopez"]
      }
    },
    {
      "type": "opinion_similarity",
      "title": "Opinion Similarity Matrix",
      "description": "Semantic similarity between agents' final opinions",
      "data": {
        "matrix": [
          [1.0, 0.23],
          [0.23, 1.0]
        ],
        "similarity_pairs": {
          "Sarah Mitchell_vs_Sarah Mitchell": 1.0,
          "Sarah Mitchell_vs_James Thompson": 0.23,
          "James Thompson_vs_Sarah Mitchell": 0.23,
          "James Thompson_vs_James Thompson": 1.0
        }
      },
      "metadata": {
        "speaking_agents": ["Sarah Mitchell", "James Thompson"],
        "similarity_range": {"min": 0.0, "max": 1.0},
        "note": "Higher values indicate more similar opinions. Only agents who spoke are included."
      }
    }
  ]
}
```

**Features:**
- **Read-only**: Does not trigger analytics computation or modify any data
- **Same Format**: Returns identical response format as `POST /simulations/{sim_id}/analyze`
- **Existence Check**: Only returns data if analytics already exist

**Error Responses:**
- `400`: Invalid simulation ID format
- `404`: Simulation not found
- `404`: No analytics found for this simulation

**Use Cases:**
- Check if analytics have been computed without accidentally triggering new computation
- Retrieve existing analytics results for display/visualization
- Validate analytics existence before performing operations that depend on analytics data

**Analytics Data Explanation:**
- **Engagement Matrix**: Shows agent activity for each debate turn (0=inactive, 1=engaged, 2=speaking)
- **Participation Stats**: Quantifies speaking time, engagement rates, and participation percentages
- **Opinion Similarity**: Matrix showing semantic similarity between agents' final opinions (0.0-1.0)

**Notes:**
- `opinion_similarity` matrix is computed using the system's shared embedding service
- Similarity values range from 0.0 (completely different) to 1.0 (identical)
- Matrix is symmetric with 1.0 on diagonal (self-similarity)

#### `GET /simulations/{sim_id}/interventions`

Retrieves all interventions (agent messages and tool usages) from a completed simulation.

**Path Parameters:**
- `sim_id` (string): UUID of the simulation

**Response:**
```json
{
  "interventions": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "run_id": "550e8400-e29b-41d4-a716-446655440001",
      "agent_name": "Conservative Economist",
      "iteration": 1,
      "content": "I believe we should consider the long-term economic impacts...",
      "tools_used": [
        {
          "tool_name": "web_search",
          "query": "minimum wage economic impact studies",
          "results": "Recent studies show mixed results..."
        }
      ],
      "timestamp": "2025-10-31T10:30:15Z"
    }
  ],
  "total": 15
}
```

#### `GET /simulations/{sim_id}/interventions/{intervention_id}/tools`

Retrieves detailed tool usage information for a specific intervention.

**Path Parameters:**
- `sim_id` (string): UUID of the simulation
- `intervention_id` (string): UUID of the intervention

**Response:**
```json
{
  "intervention_id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_name": "Conservative Economist",
  "tools": [
    {
      "tool_name": "web_search",
      "tool_type": "news_tool",
      "query": "minimum wage economic impact studies",
      "results": [
        {
          "title": "Study on Minimum Wage Effects",
          "url": "https://example.com/study",
          "content": "Research findings show..."
        }
      ],
      "metadata": {
        "search_provider": "google_news",
        "timestamp": "2025-10-31T10:30:12Z"
      }
    }
  ]
}
```

**Tool Usage Access:**
- Only the simulation owner can access intervention and tool usage details
- Tool results include the complete data that was available to agents during the debate
- Useful for understanding agent reasoning and fact-checking agent claims

---

## Error Responses

**400 Bad Request:**
```json
{
  "detail": "At least one agent must be provided"
}
```
```json
{
  "detail": "Invalid simulation ID format"
}
```
```json
{
  "detail": "Invalid agent ID format"
}
```
```json
{
  "detail": "Simulation already finished"
}
```
```json
{
  "detail": "Simulation must be finished before voting"
}
```

**404 Not Found:**
```json
{
  "detail": "Simulation not found"
}
```
```json
{
  "detail": "Agent template not found"
}
```

**422 Validation Error:**
FastAPI automatically validates request bodies and returns detailed validation errors:
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "topic"],
      "msg": "Field required",
      "input": {...}
    }
  ]
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Simulation service not initialized"
}
```
```json
{
  "detail": "Database not initialized"
}
```
```json
{
  "detail": "Failed to fetch available models: Connection timeout"
}
```
```json
{
  "detail": "Failed to fetch agent templates: Database connection failed"
}
```

