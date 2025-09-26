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

Retrieves availabl## Config Versions

Config versions provide access to historical versions of configs, preserving the complete state (parameters + agents) at each version. This enables viewing and "collapsing" past config versions into new editable configs.

### GET /config-versions/{config_id}/versions/{version_number}

Retrieves a specific config version by config ID and version number. Returns the complete config state as it existed at that version, including all agents and their configurations.age models for agent configuration.

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
    "topic": "Should artificial intelligence development be regulated by government?",
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

## Config Snapshots

Config snapshots provide access to historical versions of configs, preserving the complete state (parameters + agents) at each version. This enables viewing and "collapsing" past config versions into new editable configs.

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
    "stance": "neutral",
    "embedding_model": "onnx_minilm",
    "embedding_config": {}
  },
  "version_number": 2,
  "agents": [
    {
      "position": 1,
      "name": "Conservative Economist",
      "background": null,
      "canvas_position": {
        "x": 100.5,
        "y": 200.0
      },
      "snapshot": {
        "profile": "You are a conservative economist concerned about fiscal policy...",
        "model_id": "openai/gpt-4o"
      },
      "created_at": "2025-09-24T00:00:00Z"
    },
    {
      "position": 2,
      "name": "Progressive Activist",
      "background": null,
      "canvas_position": {
        "x": 300.0,
        "y": 150.75
      },
      "snapshot": {
        "profile": "You are a progressive activist focused on workers' rights...",
        "model_id": "anthropic/claude-3.5-sonnet"
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

#### `GET /simulations/{sim_id}/analytics`

Retrieves analytics and visualizations data for a completed simulation. Analytics are computed on first request and cached for subsequent calls.

**Path Parameters:**
- `sim_id` (string): Simulation ID

**Response:**
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "engagement_matrix": {
    "data": [
      [2, 0, 1, 0, 1],
      [1, 2, 0, 1, 0],
      [0, 1, 2, 1, 1]
    ],
    "agent_names": ["Sarah Mitchell", "James Thompson", "Maria Lopez"],
    "turn_count": 5,
    "legend": {
      "0": "inactive",
      "1": "engaged",
      "2": "speaking"
    }
  },
  "participation_stats": {
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
  "opinion_similarity": {
    "matrix": [
      [1.0, 0.23, 0.87],
      [0.23, 1.0, 0.34],
      [0.87, 0.34, 1.0]
    ],
    "agent_names": ["Sarah Mitchell", "James Thompson", "Maria Lopez"]
  },
  "computed_at": "2025-09-26T10:30:00"
}
```

**Requirements:**
- Simulation must have `status: "finished"`
- Analytics are computed once and cached for performance

**Use Cases:**
- Generate engagement heatmaps showing who participated when
- Create participation charts showing speaking time distribution
- Build opinion similarity matrices/clustermaps for consensus analysis
- Analyze debate dynamics and agent interaction patterns

**Notes:**
- `opinion_similarity` matrix is only included if embedding model is available
- Similarity values range from 0.0 (completely different) to 1.0 (identical)
- Matrix is symmetric with 1.0 on diagonal (self-similarity)

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

