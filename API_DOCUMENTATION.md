# Debate Agents API Documentation

## Overview

A FastAPI-based backend service for AI-powered debates between multiple agents with configurable personalities and language models.

## Base URL

```
http://localhost:8000
```

## Authentication

No authentication required.

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

Retrieves available language models for agent configuration.

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

## Agent Templates

#### `GET /agents/templates`

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
        "temperature": 0.7,
        "max_tokens": 500,
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

Retrieves a specific agent template by ID.

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
    "temperature": 0.7,
    "max_tokens": 500,
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

Retrieves public config templates that can be used for simulations. These are immutable blueprints that define debate parameters and agent configurations.

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
        "embedding_model": "onnx_minilm",
        "agent_count": 3
      },
      "created_at": "2025-09-03T10:30:00Z"
    }
  ],
  "total": 3
}
```

#### `GET /config-templates/{template_id}`

Retrieves a specific public config template by ID.

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
    "embedding_model": "onnx_minilm",
    "agent_count": 3
  },
  "agents": [
    {
      "position": 1,
      "name": "Conservative Economist",
      "background": "PhD in Economics, specializes in fiscal policy",
      "snapshot": {
        "profile": "You are a conservative economist...",
        "model_id": "openai/gpt-4o"
      },
      "created_at": "2025-09-03T10:30:00Z"
    },
    {
      "position": 2,
      "name": "Progressive Activist",
      "background": "Labor rights advocate",
      "snapshot": {
        "profile": "You are a progressive activist...",
        "model_id": "openai/gpt-4o-mini"
      },
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
- **Versioning**: Parameters changes increment version number, agent changes are tracked in snapshots

#### `GET /configs`

Retrieves public configs that can be used for simulations. These are editable instances that can be modified and used as starting points for debates.

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
        "embedding_model": "onnx_minilm",
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
    "topic": "",
    "max_iters": 21,
    "bias": [],
    "stance": "",
    "embedding_model": "onnx_minilm",
    "embedding_config": {}
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
      "model_id": "openai/gpt-4o"
    }
  ],
  "max_iters": 15,
  "bias": [0.5, -0.3],
  "stance": "pro-increase",
  "embedding_model": "onnx_minilm"
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
    "stance": "pro-increase",
    "embedding_model": "onnx_minilm",
    "embedding_config": {}
  },
  "version_number": 2,
  "agents": [...],
  "source_template_id": null,
  "created_at": "2025-09-03T12:00:00Z",
  "updated_at": "2025-09-03T12:05:00Z"
}
```

**Important Notes:**
- **Agent Data Storage**: Agents are stored separately from config parameters. Agent data (including canvas positions) is stored in dedicated agent snapshot records, not in the `parameters` field.
- **Canvas Positioning**: Each agent can have optional `canvas_position` with `x` and `y` coordinates for UI layout.

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
    "embedding_model": "onnx_minilm",
    "agent_count": 3
  },
  "version_number": 2,
  "source_template_id": "550e8400-e29b-41d4-a716-446655440001",
  "agents": [
    {
      "position": 1,
      "name": "Conservative Economist",
      "background": "PhD in Economics, specializes in fiscal policy",
      "snapshot": {
        "profile": "You are a conservative economist...",
        "model_id": "openai/gpt-4o"
      },
      "created_at": "2025-09-03T10:30:00Z"
    },
    {
      "position": 2,
      "name": "Progressive Activist",
      "background": "Labor rights advocate, modified for stronger stance",
      "snapshot": {
        "profile": "You are a progressive activist with strong views...",
        "model_id": "openai/gpt-4o-mini"
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
      "model_id": "openai/gpt-4o"
    },
    {
      "name": "PrivacyAdvocate", 
      "profile": "You are a privacy rights advocate",
      "model_id": "anthropic/claude-3.5-sonnet"
    }
  ],
  "max_iters": 21,
  "bias": [0.1, 0.2],
  "stance": "pro-regulation",
  "embedding_model": "onnx_minilm",
  "embedding_config": {
    "model_name": "openai/text-embedding-3-small"
  }
}
```

**Required Fields:**
- `topic` (string): The debate topic
- `agents` (array): Agent configurations
  - `name` (string): Agent name
  - `profile` (string): Background description
  - `model_id` (string, optional): Language model ID

**Optional Fields:**
- `config_id` (string): Existing config ID to auto-save changes to
- `config_name` (string, default: "Untitled Simulation"): Name for auto-saved config
- `config_description` (string): Description for auto-saved config
- `max_iters` (integer, default: 21): Maximum iterations
- `bias` (array of floats): Bias weights for each agent
- `stance` (string): Initial stance
- `embedding_model` (string, default: "onnx_minilm"): Embedding model type
- `embedding_config` (object): Additional embedding configuration

**Auto-Save Behavior:**
- If `config_id` is provided, the backend will check if the simulation parameters differ from the stored config
- If different, it automatically creates a new version of the config and increments the version number
- This allows tracking which version of a config was used for each simulation run**Response:**
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
      "timestamp": "2025-08-30T01:05:04.072115"
    }
  ],
  "is_finished": false,
  "stopped_reason": null,
  "started_at": "2025-08-30T01:04:55.123456",
  "finished_at": null,
  "created_at": "2025-08-30T01:04:54.987654"
}
```

**New Fields:**
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

Triggers voting for a completed simulation.

**Path Parameters:**
- `sim_id` (string): Simulation ID

**Response:**
```json
{
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "yea": 2,
  "nay": 1,
  "reasons": [
    "TechExec: While I support innovation, some basic safety regulations are necessary",
    "PrivacyAdvocate: Strong regulations are essential to protect citizen privacy"
  ]
}
```

**Requirements:**
- Simulation must have `status: "finished"`

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

