# Debate Agents API Documentation

## Overview

The Debate Agents API is a FastAPI-based backend service that orchestrates AI-powered debates between multiple agents. Each agent has unique profiles and backgrounds, and they engage in structured debates on specified topics using GPT-4o-mini for reasoning and stance-aware SBERT for semantic understanding.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, no authentication is required.

---

## Endpoints

### Health Check

#### `GET /healthz`

Basic health check endpoint to verify the service is running.

**Response:**
```json
{
  "ok": true
}
```

---

### Simulation Management

All simulation endpoints are prefixed with `/simulations`.

#### `POST /simulations`

Creates a new debate simulation with specified agents and topic.

**Request Body:**
```json
{
  "topic": "Should artificial intelligence be regulated by governments?",
  "profiles": [
    "You are a tech industry executive who believes in innovation and minimal regulation",
    "You are a privacy rights advocate concerned about AI surveillance",
    "You are a policy researcher focused on balanced regulation"
  ],
  "agent_names": ["TechExec", "PrivacyAdvocate", "PolicyExpert"],
  "max_iters": 21,
  "bias": [0.1, 0.2, 0.15],
  "stance": "pro-regulation"
}
```

**Required Fields:**
- `topic` (string): The debate topic
- `profiles` (array of strings): Background descriptions for each agent
- `agent_names` (array of strings): Names for each agent

**Optional Fields:**
- `max_iters` (integer, default: 21): Maximum number of debate iterations
- `bias` (array of floats): Bias weights for each agent (must match agent count)
- `stance` (string): Initial stance for the debate

**Validation:**
- `profiles` and `agent_names` arrays must have the same length

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "snapshot": {
    "topic": "Should artificial intelligence be regulated by governments?",
    "max_iters": 21,
    "iters": 0,
    "finished": false,
    "agents": [...],
    "intervenciones": [],
    "engagement_log": [],
    "opiniones": [],
    "moderator": {...}
  }
}
```

---

#### `POST /simulations/{sim_id}/start`

Initializes and starts the debate simulation.

**Path Parameters:**
- `sim_id` (string): The simulation ID returned from creation

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "snapshot": {
    "topic": "Should artificial intelligence be regulated by governments?",
    "max_iters": 21,
    "iters": 0,
    "finished": false,
    "agents": [
      {
        "id": "agent_uuid",
        "name": "TechExec",
        "background": "You are a tech industry executive...",
        "last_opinion": "",
        "memory": []
      }
    ],
    "intervenciones": [],
    "engagement_log": [],
    "opiniones": [],
    "moderator": {
      "interventions": [],
      "hands_raised": [],
      "weight": [],
      "bias": [0.1, 0.2, 0.15]
    }
  }
}
```

---

#### `POST /simulations/{sim_id}/step`

Advances the simulation by one turn/iteration. Use this for step-by-step control of the debate.

**Path Parameters:**
- `sim_id` (string): The simulation ID

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "event": {
    "iteration": 1,
    "speaker": "TechExec",
    "opinion": "I believe that excessive regulation could stifle innovation in the AI sector...",
    "engaged": ["PrivacyAdvocate", "PolicyExpert"],
    "finished": false,
    "stopped_reason": null
  },
  "snapshot": {
    // Full simulation state after the step
  }
}
```

**Event Object:**
- `iteration` (integer): Current iteration number
- `speaker` (string): Name of the agent who spoke this turn
- `opinion` (string): The opinion/statement made by the speaker
- `engaged` (array of strings): Names of agents who want to respond
- `finished` (boolean): Whether the simulation has ended
- `stopped_reason` (string, nullable): Reason for stopping if finished

**Possible Stop Reasons:**
- `"no_one_wants_to_continue"`: No agents want to continue the debate
- `"comments_too_similar"`: Agent responses have become too similar (lack of diversity)
- `"max_iters_reached"`: Maximum number of iterations reached

---

#### `POST /simulations/{sim_id}/run`

Runs the simulation to completion automatically. Use this to let the debate run without manual intervention.

**Path Parameters:**
- `sim_id` (string): The simulation ID

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "snapshot": {
    // Final simulation state
    "finished": true,
    "iters": 15,
    // ... rest of snapshot
  }
}
```

---

#### `POST /simulations/{sim_id}/vote`

Triggers all agents to vote on the debate topic and provide their reasoning.

**Path Parameters:**
- `sim_id` (string): The simulation ID

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "yea": 2,
  "nay": 1,
  "reasons": [
    "TechExec: While I support innovation, some basic safety regulations are necessary",
    "PrivacyAdvocate: Strong regulations are essential to protect citizen privacy",
    "PolicyExpert: Balanced regulation can foster both innovation and safety"
  ]
}
```

**Response Fields:**
- `yea` (integer): Number of agents voting in favor
- `nay` (integer): Number of agents voting against
- `reasons` (array of strings): Detailed reasoning from each agent

---

#### `POST /simulations/{sim_id}/stop`

Manually stops a running simulation before it reaches natural completion.

**Path Parameters:**
- `sim_id` (string): The simulation ID

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "snapshot": {
    "finished": true,
    // ... current state
  }
}
```

---

#### `GET /simulations/{sim_id}`

Retrieves the current state/snapshot of a simulation without advancing it.

**Path Parameters:**
- `sim_id` (string): The simulation ID

**Response:**
```json
{
  "topic": "Should artificial intelligence be regulated by governments?",
  "max_iters": 21,
  "iters": 5,
  "finished": false,
  "agents": [
    {
      "id": "agent_uuid",
      "name": "TechExec",
      "background": "You are a tech industry executive who believes in innovation and minimal regulation",
      "last_opinion": "I believe we need to be careful not to over-regulate...",
      "memory": [
        "PrivacyAdvocate mentioned concerns about surveillance",
        "PolicyExpert suggested a balanced approach"
      ]
    }
  ],
  "intervenciones": ["TechExec", "PrivacyAdvocate", "PolicyExpert", "TechExec", "PrivacyAdvocate"],
  "engagement_log": [
    ["PrivacyAdvocate", "PolicyExpert"],
    ["TechExec", "PolicyExpert"],
    ["TechExec", "PrivacyAdvocate"]
  ],
  "opiniones": [
    "Innovation requires freedom to experiment and iterate quickly...",
    "We must prioritize protecting citizens from potential AI misuse...",
    "A measured regulatory approach can balance innovation with safety..."
  ],
  "moderator": {
    "interventions": [],
    "hands_raised": ["PolicyExpert"],
    "weight": [0.33, 0.33, 0.34],
    "bias": [0.1, 0.2, 0.15]
  }
}
```

**Snapshot Object Fields:**
- `topic`: The debate topic
- `max_iters`: Maximum allowed iterations
- `iters`: Current iteration count
- `finished`: Whether the simulation has ended
- `agents`: Array of agent objects with their current state
- `intervenciones`: Chronological list of speaker names
- `engagement_log`: For each turn, which agents wanted to respond
- `opiniones`: Chronological list of all opinions expressed
- `moderator`: Moderator state including current speakers queue and bias settings

---

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "profiles and agent_names must have same length"
}
```

### 404 Not Found
```json
{
  "detail": "Simulation not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Simulation service not initialized"
}
```

---

## Usage Flow Examples

### Basic Debate Flow

1. **Create a simulation:**
   ```bash
   POST /simulations
   # Returns simulation ID
   ```

2. **Start the debate:**
   ```bash
   POST /simulations/{sim_id}/start
   ```

3. **Run step-by-step OR run to completion:**
   
   **Option A - Step by step:**
   ```bash
   POST /simulations/{sim_id}/step  # Repeat as needed
   ```
   
   **Option B - Run to completion:**
   ```bash
   POST /simulations/{sim_id}/run
   ```

4. **Get final votes:**
   ```bash
   POST /simulations/{sim_id}/vote
   ```

### Monitoring Progress

- Use `GET /simulations/{sim_id}` at any time to check current state
- Monitor the `finished` field to know when debate has ended
- Check `engagement_log` to see participation patterns

---

## Frontend Integration Notes

### WebSocket Alternative
Currently, the API uses HTTP endpoints. For real-time updates, consider implementing WebSocket connections for live debate streaming.

### State Management
- Store the `sim_id` after creation for subsequent API calls
- The `snapshot` object contains all necessary state information
- Use the `event` object from `/step` for turn-by-turn updates

### UI Considerations
- Display `intervenciones` and `opiniones` arrays in chronological order
- Show `engagement_log` to visualize which agents are active each turn
- Use `finished` and `stopped_reason` to handle debate completion
- Display voting results from the `/vote` endpoint

### Performance
- Simulations may take several seconds per step due to AI processing
- Consider implementing loading states for API calls
- The `/run` endpoint may take longer as it processes the entire debate

---

## Technical Details

- **AI Model**: GPT-4o-mini for agent reasoning
- **Semantic Analysis**: Stance-aware SBERT for understanding positions
- **Framework**: FastAPI with async support
- **Response Format**: JSON for all endpoints
- **Error Handling**: Standard HTTP status codes with detailed messages
