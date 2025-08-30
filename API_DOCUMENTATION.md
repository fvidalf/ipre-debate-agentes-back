# Debate Agents API Documentation (v3.0)

## Overview

The Debate Agents API is a FastAPI-based backend service that orchestrates AI-powered debates between multiple agents. Each agent has unique profiles, backgrounds, and can use different language models for personalized responses. The API uses OpenRouter to provide access to various AI models and configurable embedding models for semantic understanding.

### Major v3.0 Changes

🎯 **Simplified API**: Reduced from 6 endpoints to 3 clean endpoints - no more create→start→run complexity

🔄 **Background Processing**: Simulations run automatically in the background with real-time status polling

� **Persistent Storage**: All simulations and events are stored in the database for full audit trail

� **One-Click Execution**: Single API call creates AND runs the simulation - matches user expectations

### Key Features

- **Per-Agent Model Selection**: Each agent can use a different language model for diverse response styles
- **Dynamic Model Discovery**: Available models are fetched from OpenRouter API in real-time
- **Background Simulation Processing**: No blocking API calls - simulations run in background tasks
- **Real-time Progress Tracking**: Poll for live updates during simulation execution
- **Persistent Event Storage**: Complete debate history stored in database
- **Configurable Embedding Models**: Support for OpenRouter embeddings or local ONNX models

For detailed setup instructions, see the [Embedding Models Documentation](docs/embedding-models.md).

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, no authentication is required (mock user is created automatically).

---

## API Endpoints

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

### Available Models

#### `GET /simulations/models`

Retrieves the list of available language models for agent configuration. Models are fetched dynamically from OpenRouter API.

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
      "description": "Faster and cheaper version of GPT-4o, good balance of capability and cost",
      "provider": "openai"
    },
    {
      "id": "anthropic/claude-3.5-sonnet",
      "name": "Claude 3.5 Sonnet",
      "description": "Anthropic's most capable model, excellent for nuanced discussions",
      "provider": "anthropic"
    }
  ],
  "default_model": "openai/gpt-4o-mini"
}
```

**Notes:**
- Models are cached for performance
- If OpenRouter API is unavailable, returns a curated fallback list
- Only models suitable for debate agents are included

---

## Simulation Management

All simulation endpoints are prefixed with `/simulations`.

### `POST /simulations`

Creates a new debate simulation and immediately starts running it in the background. This is the main endpoint that replaces the old create→start→run flow.

**Request Body:**
```json
{
  "topic": "Should artificial intelligence be regulated by governments?",
  "agents": [
    {
      "name": "TechExec",
      "profile": "You are a tech industry executive who believes in innovation and minimal regulation",
      "model_id": "openai/gpt-4o"
    },
    {
      "name": "PrivacyAdvocate", 
      "profile": "You are a privacy rights advocate concerned about AI surveillance",
      "model_id": "anthropic/claude-3.5-sonnet"
    },
    {
      "name": "PolicyExpert",
      "profile": "You are a policy researcher focused on balanced regulation",
      "model_id": "openai/gpt-4o-mini"
    }
  ],
  "max_iters": 21,
  "bias": [0.1, 0.2, 0.15],
  "stance": "pro-regulation",
  "embedding_model": "openrouter",
  "embedding_config": {
    "model_name": "openai/text-embedding-3-small"
  }
}
```

**Required Fields:**
- `topic` (string): The debate topic
- `agents` (array of objects): Agent configurations, each containing:
  - `name` (string): Agent name
  - `profile` (string): Background description for the agent
  - `model_id` (string, optional): Language model ID for this agent (from `/simulations/models`)

**Optional Fields:**
- `max_iters` (integer, default: 21): Maximum number of debate iterations
- `bias` (array of floats): Bias weights for each agent (must match agent count)
- `stance` (string): Initial stance for the debate
- `embedding_model` (string, default: "onnx_minilm"): Embedding model type ("openrouter" or "onnx_minilm")
- `embedding_config` (object): Additional configuration for the embedding model

**Response:**
```json
{
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "created",
  "message": "Simulation started, use GET /simulations/{id} to check progress"
}
```

**What happens after this call:**
1. Simulation is created and stored in database
2. Background task starts immediately
3. Agents are initialized with their specified models
4. Debate begins automatically
5. Use `GET /simulations/{id}` to monitor progress

---

### `GET /simulations/{sim_id}`

Retrieves the current status and progress of a running or completed simulation. Use this endpoint to poll for real-time updates.

**Path Parameters:**
- `sim_id` (string): The simulation ID returned from creation

**Response:**
```json
{
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
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
      "opinion": "I believe that excessive regulation could stifle innovation in the AI sector...",
      "engaged": ["PrivacyAdvocate", "PolicyExpert"],
      "finished": false,
      "timestamp": "2025-08-30T01:05:04.072115"
    },
    {
      "iteration": 5,
      "speaker": "PrivacyAdvocate",
      "opinion": "While innovation is important, we must prioritize protecting citizens...",
      "engaged": ["TechExec", "PolicyExpert"],
      "finished": false,
      "timestamp": "2025-08-30T01:05:07.058524"
    }
  ],
  "is_finished": false,
  "stopped_reason": null,
  "started_at": "2025-08-30T01:04:55.123456",
  "finished_at": null,
  "created_at": "2025-08-30T01:04:54.987654"
}
```

**Status Values:**
- `"created"`: Simulation just created, background task starting
- `"running"`: Simulation is actively running
- `"finished"`: Simulation completed successfully
- `"failed"`: Simulation encountered an error
- `"stopped"`: Simulation was manually stopped

**Polling Recommendations:**
- Poll every 2-3 seconds during active simulations
- Check `is_finished` to know when to stop polling
- `latest_events` shows the most recent 10 debate steps
- `progress.percentage` gives overall completion status

---

### `POST /simulations/{sim_id}/stop`

Manually stops a running simulation before it reaches natural completion.

**Path Parameters:**
- `sim_id` (string): The simulation ID

**Response:**
```json
{
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "stopped",
  "message": "Stop request submitted"
}
```

**Notes:**
- The background task will detect the stop request and halt gracefully
- Events generated up to the stop point are preserved
- Use `GET /simulations/{id}` to confirm the simulation has stopped

---

### `POST /simulations/{sim_id}/vote`

Triggers all agents to vote on the debate topic and provide their reasoning. Only available for completed simulations.

**Path Parameters:**
- `sim_id` (string): The simulation ID

**Response:**
```json
{
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "yea": 2,
  "nay": 1,
  "reasons": [
    "TechExec: While I support innovation, some basic safety regulations are necessary",
    "PrivacyAdvocate: Strong regulations are essential to protect citizen privacy",
    "PolicyExpert: Balanced regulation can foster both innovation and safety"
  ]
}
```

**Requirements:**
- Simulation must have `status: "finished"`
- Returns HTTP 400 if simulation is not yet complete

---

## Usage Flow Examples

### Basic Debate Flow (New Simplified Version)

```javascript
// 1. Create and start simulation (single call!)
const response = await fetch('/simulations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    topic: "Should AI be regulated?",
    agents: [
      {
        name: "TechInnovator",
        profile: "You are a Silicon Valley tech executive...",
        model_id: "openai/gpt-4o-mini"
      },
      {
        name: "EthicsAdvocate", 
        profile: "You are an AI ethics researcher...",
        model_id: "anthropic/claude-3.5-haiku"
      }
    ],
    max_iters: 10
  })
});

const { simulation_id } = await response.json();

// 2. Poll for updates
async function pollForUpdates() {
  const statusResponse = await fetch(`/simulations/${simulation_id}`);
  const status = await statusResponse.json();
  
  // Update UI with progress
  updateProgress(status.progress.percentage);
  
  // Show latest debate events
  status.latest_events.forEach(event => {
    addDebateStep(event.speaker, event.opinion, event.iteration);
  });
  
  // Check if finished
  if (status.is_finished) {
    showFinalResults(status);
    
    // Trigger voting
    const voteResponse = await fetch(`/simulations/${simulation_id}/vote`, {
      method: 'POST'
    });
    const votes = await voteResponse.json();
    showVotingResults(votes);
  } else {
    // Continue polling
    setTimeout(pollForUpdates, 2000);
  }
}

// Start polling
pollForUpdates();
```

### Frontend Integration Example

```javascript
class DebateSimulation {
  constructor(config) {
    this.config = config;
    this.simulationId = null;
    this.pollInterval = null;
    this.onUpdate = null;
  }

  async start() {
    // Create and start simulation
    const response = await fetch('/simulations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(this.config)
    });
    
    const result = await response.json();
    this.simulationId = result.simulation_id;
    
    // Start polling for updates
    this.startPolling();
    
    return this.simulationId;
  }

  startPolling() {
    this.pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/simulations/${this.simulationId}`);
        const status = await response.json();
        
        if (this.onUpdate) {
          this.onUpdate(status);
        }
        
        // Stop polling when finished
        if (status.is_finished) {
          this.stopPolling();
        }
        
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 2000); // Poll every 2 seconds
  }

  stopPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  async stop() {
    if (this.simulationId) {
      await fetch(`/simulations/${this.simulationId}/stop`, { 
        method: 'POST' 
      });
    }
    this.stopPolling();
  }
}

// Usage
const debate = new DebateSimulation(config);

debate.onUpdate = (status) => {
  // Update progress bar
  document.getElementById('progress').style.width = 
    `${status.progress.percentage}%`;
  
  // Add new debate events
  status.latest_events.forEach(event => {
    addMessageToDebate(event.speaker, event.opinion);
  });
  
  // Show completion
  if (status.is_finished) {
    showCompletionMessage(status.stopped_reason);
  }
};

await debate.start();
```

## Error Handling

### Common Error Responses

**400 Bad Request:**
```json
{
  "detail": "At least one agent must be provided"
}
```

**404 Not Found:**
```json
{
  "detail": "Simulation not found"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Failed to fetch available models: Connection error"
}
```

### Simulation Status Error States

When `status: "failed"`, the `stopped_reason` field contains the error message:
```json
{
  "status": "failed",
  "stopped_reason": "litellm.APIConnectionError: AnthropicException",
  "is_finished": true
}
```

## Migration from v2.x API

### Old API (deprecated)
```javascript
// Old way - multiple API calls
const { id } = await fetch('/simulations', { method: 'POST', body: config });
await fetch(`/simulations/${id}/start`, { method: 'POST' });
await fetch(`/simulations/${id}/run`, { method: 'POST' });
```

### New API (v3.0)
```javascript
// New way - single API call + polling
const { simulation_id } = await fetch('/simulations', { 
  method: 'POST', 
  body: config 
});

// Poll for progress
const status = await fetch(`/simulations/${simulation_id}`);
```

## Performance and Scaling

- **Background Processing**: Simulations don't block API responses
- **Database Storage**: All events persisted for audit trail and analytics
- **Polling Efficiency**: Latest events limited to 10 most recent to minimize response size
- **Model Caching**: Available models cached to reduce OpenRouter API calls
- **Memory Management**: Simulation objects cleaned up after completion

---

*For technical support or feature requests, please refer to the project repository.*
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

## Frontend Integration Examples

### Complete Workflow Example

Here's a complete example of how the frontend should interact with the new per-agent model API:

#### 1. Fetch Available Models
```javascript
// Get available models for agent configuration
const modelsResponse = await fetch('/simulations/models');
const { models, default_model } = await modelsResponse.json();

// Example response:
// {
//   "models": [
//     {
//       "id": "openai/gpt-4o",
//       "name": "GPT-4o", 
//       "description": "Most capable OpenAI model...",
//       "provider": "openai"
//     },
//     // ... more models
//   ],
//   "default_model": "openai/gpt-4o-mini"
// }
```

#### 2. Create Simulation with Agent-Specific Models
```javascript
// Configure agents with different models for diverse perspectives
const simulationConfig = {
  topic: "Should artificial intelligence be regulated by governments?",
  agents: [
    {
      name: "TechInnovator",
      profile: "You are a Silicon Valley tech executive who believes in rapid innovation and minimal government interference",
      model_id: "openai/gpt-4o"  // Use GPT-4o for nuanced business perspective
    },
    {
      name: "EthicsAdvocate",
      profile: "You are an AI ethics researcher concerned about potential societal harms and bias",
      model_id: "anthropic/claude-3.5-sonnet"  // Use Claude for ethical reasoning
    },
    {
      name: "PolicyMaker",
      profile: "You are a government official tasked with creating balanced technology policies",
      model_id: "openai/gpt-4o-mini"  // Use efficient model for policy analysis
    },
    {
      name: "CitizenRep",
      profile: "You represent the average citizen's concerns about AI in daily life",
      model_id: null  // Use default model
    }
  ],
  max_iters: 15,
  embedding_model: "openrouter"
};

const createResponse = await fetch('/simulations', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(simulationConfig)
});

const { id: simId } = await createResponse.json();
```

#### 3. Run the Debate
```javascript
// Start the simulation
await fetch(`/simulations/${simId}/start`, { method: 'POST' });

// Option A: Step-by-step for real-time updates
async function runStepByStep() {
  let finished = false;
  while (!finished) {
    const stepResponse = await fetch(`/simulations/${simId}/step`, { method: 'POST' });
    const { event } = await stepResponse.json();
    
    // Update UI with new opinion
    displayNewOpinion(event.speaker, event.opinion);
    updateEngagement(event.engaged);
    
    finished = event.finished;
    
    // Add delay for better UX
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
}

// Option B: Run to completion
async function runToCompletion() {
  await fetch(`/simulations/${simId}/run`, { method: 'POST' });
  
  // Get final snapshot
  const snapshot = await fetch(`/simulations/${simId}`);
  const finalState = await snapshot.json();
  displayFinalDebate(finalState);
}
```

#### 4. Get Voting Results
```javascript
// Get final votes and reasoning
const voteResponse = await fetch(`/simulations/${simId}/vote`, { method: 'POST' });
const { yea, nay, reasons } = await voteResponse.json();

displayVotingResults(yea, nay, reasons);
```

### Model Selection Best Practices

1. **Diverse Perspectives**: Use different models for different agent types to get varied reasoning styles
2. **Cost Optimization**: Use efficient models (like `gpt-4o-mini`) for agents that participate frequently
3. **Specialized Reasoning**: Use models like Claude for ethics-focused agents, GPT-4o for complex business reasoning
4. **Fallback Strategy**: Always have a default model configured; invalid models automatically fall back

### UI Components Suggestions

```javascript
// Model Selector Component
function ModelSelector({ availableModels, selectedModel, onModelChange, agentName }) {
  return (
    <select value={selectedModel || ''} onChange={(e) => onModelChange(e.target.value)}>
      <option value="">Use Default ({defaultModel})</option>
      {availableModels.map(model => (
        <option key={model.id} value={model.id}>
          {model.name} ({model.provider})
        </option>
      ))}
    </select>
  );
}

// Agent Configuration Form
function AgentConfigForm({ onSubmit }) {
  const [agents, setAgents] = useState([
    { name: '', profile: '', model_id: null }
  ]);
  
  // ... form logic
}
```

---

## Technical Details

- **AI Models**: Per-agent customizable models via OpenRouter API
- **Semantic Analysis**: Stance-aware SBERT for understanding positions  
- **Framework**: FastAPI with async support
- **Response Format**: JSON for all endpoints
- **Error Handling**: Standard HTTP status codes with detailed messages
- **Model Management**: Dynamic model discovery with intelligent fallbacks
