# BREAKING CHANGES DOCUMENTATION - Data Model Migration

## Overview
We've completely replaced the old `RunEvent` table with a new enhanced data model that supports interventions, tool usage, documents, and embeddings. This is a **BREAKING CHANGE** that requires frontend updates.

## Database Schema Changes

### 1. REMOVED: `RunEvent` table
The old `run_events` table has been completely removed and replaced.

### 2. NEW: `Intervention` table (replaces RunEvent)
```sql
CREATE TABLE interventions (
    id UUID PRIMARY KEY,
    run_id UUID NOT NULL,
    iteration INTEGER NOT NULL,
    speaker VARCHAR NOT NULL,
    content TEXT NOT NULL,           -- Was "opinion" in RunEvent
    engaged_agents TEXT[] NOT NULL,  -- Was "engaged" in RunEvent
    reasoning_steps JSONB,           -- NEW: Internal reasoning for frontend
    finished BOOLEAN DEFAULT FALSE,
    stopped_reason VARCHAR,
    created_at TIMESTAMP
);
```

### 3. NEW: `ToolUsage` table
```sql
CREATE TABLE tool_usages (
    id UUID PRIMARY KEY,
    intervention_id UUID NOT NULL,
    agent_name VARCHAR NOT NULL,
    tool_name VARCHAR NOT NULL,
    query TEXT NOT NULL,            -- Embeddable
    output TEXT NOT NULL,           -- Embeddable
    raw_results JSONB,              -- Full tool data for debugging
    execution_time FLOAT,
    created_at TIMESTAMP
);
```

### 4. NEW: `Document` table
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    agent_name VARCHAR NOT NULL,
    run_id UUID NOT NULL,
    title VARCHAR NOT NULL,
    content TEXT NOT NULL,          -- Embeddable
    document_type VARCHAR NOT NULL,
    source_url VARCHAR,
    file_name VARCHAR,
    file_size INTEGER,
    upload_user_id UUID NOT NULL,
    created_at TIMESTAMP
);
```

### 5. NEW: `Embedding` table
```sql
CREATE TABLE embeddings (
    id UUID PRIMARY KEY,
    source_type VARCHAR NOT NULL,    -- 'intervention', 'tool_query', 'tool_output', 'document'
    source_id UUID NOT NULL,
    text_content TEXT NOT NULL,
    visibility VARCHAR NOT NULL,     -- 'public' (interventions) or 'private' (tools/docs)
    owner_agent VARCHAR,             -- For private embeddings
    run_id UUID NOT NULL,
    embedding VECTOR(384) NOT NULL,  -- pgvector type
    embedding_model VARCHAR NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP
);
```

## API Changes

### 1. BREAKING: `GET /simulations/{sim_id}` Response
**WHAT BREAKS:** The response structure looks the same, but the underlying data is completely different.

**Issues:**
- All existing simulation data (from `run_events` table) is **GONE**
- Only NEW simulations created after migration will show data
- Historical simulations will return empty `latest_events: []`

**Response structure is preserved:**
```json
{
  "latest_events": [
    {
      "iteration": 1,
      "speaker": "Agent A", 
      "opinion": "...",     // Maps from intervention.content
      "engaged": ["Agent B"], // Maps from intervention.engaged_agents
      "finished": false,
      "timestamp": "..."
    }
  ]
}
```

**FRONTEND ACTION REQUIRED:** 
- Test with NEW simulations only
- All historical simulation data is lost
- No code changes needed for basic display, but data is gone

### 2. NEW: Enhanced Intervention Endpoints

#### `GET /simulations/{sim_id}/interventions`
Get rich intervention data with optional reasoning and tool usage.

**Query Parameters:**
- `include_reasoning=true` - Include internal reasoning steps
- `include_tools=true` - Include tool usage data

**Response:**
```json
{
  "simulation_id": "...",
  "interventions": [
    {
      "id": "intervention-uuid",
      "iteration": 1,
      "speaker": "Agent A",
      "content": "...",                    // Main intervention text
      "engaged_agents": ["Agent B"],
      "finished": false,
      "stopped_reason": null,
      "created_at": "...",
      "reasoning_steps": ["...", "..."],  // If include_reasoning=true
      "tool_usages": [                    // If include_tools=true
        {
          "id": "tool-uuid",
          "tool_name": "web_search",
          "query": "...",
          "output": "...",
          "execution_time": 1.5,
          "created_at": "..."
        }
      ]
    }
  ],
  "total": 10
}
```

#### `GET /simulations/{sim_id}/interventions/{intervention_id}/tools`
Get detailed tool usage for a specific intervention.

**Query Parameters:**
- `agent_name` - Filter by specific agent (optional)

### 3. NEW: Document Management Endpoints

#### `POST /documents/{run_id}/upload`
Upload documents for agents (BEFORE simulation starts).

**Form Data:**
- `agent_name` - Owner agent name
- `title` - Document title
- `document_type` - Type ('research_paper', 'briefing', etc.)
- `file` - UTF-8 text file

#### `GET /documents/{run_id}`
List documents for a run.

**Query Parameters:**
- `agent_name` - Filter by agent (optional)

#### `GET /documents/{run_id}/{document_id}`
Get full document content.

#### `DELETE /documents/{run_id}/{document_id}`
Delete document (only before simulation starts).

## Frontend Migration Requirements

### 1. Update Simulation Display
- **No changes needed** for basic simulation display - the response format is preserved
- **Optional:** Use new `/interventions` endpoint for richer data display

### 2. Add Tool Usage Display
If showing tool usage in the frontend:
```javascript
// Get interventions with tool data
const response = await fetch(`/simulations/${simId}/interventions?include_tools=true&include_reasoning=true`);
const data = await response.json();

data.interventions.forEach(intervention => {
  // Display main intervention
  console.log(`${intervention.speaker}: ${intervention.content}`);
  
  // Display reasoning if available
  if (intervention.reasoning_steps) {
    console.log('Reasoning:', intervention.reasoning_steps);
  }
  
  // Display tool usage if available
  if (intervention.tool_usages) {
    intervention.tool_usages.forEach(tool => {
      console.log(`Used ${tool.tool_name}: ${tool.query} → ${tool.output}`);
    });
  }
});
```

### 3. Add Document Upload Interface
Before starting a simulation:
```javascript
// Upload document for an agent
const formData = new FormData();
formData.append('agent_name', 'Agent A');
formData.append('title', 'Research Brief');
formData.append('document_type', 'briefing');
formData.append('file', fileInput.files[0]);

await fetch(`/documents/${runId}/upload`, {
  method: 'POST',
  body: formData
});
```

### 4. Analytics Updates
Analytics endpoints continue to work, but now use the new `Intervention` table internally.

## Privacy Model
- **Interventions**: PUBLIC - all agents can see via embeddings
- **Tool Usage**: PRIVATE - only the owning agent can access via embeddings
- **Documents**: PRIVATE - only the owning agent can access via embeddings

## Embedding Integration (Future)
The new embedding system supports:
- RAG on public interventions
- Agent-specific RAG on private tools/documents
- Cross-content similarity search
- Vector similarity queries using pgvector

## Migration Steps

1. **Install pgvector dependency**:
   ```bash
   pip install pgvector==0.2.5
   ```

2. **Run database migration**:
   ```bash
   python -m app.database.cli migrate
   ```

3. **Update frontend code** (optional - basic display still works)

4. **Test document upload and enhanced intervention endpoints**

## Backward Compatibility

**ZERO BACKWARD COMPATIBILITY** - This is a complete nuclear replacement:

### What WILL Break at the Interface Level:
1. **All historical simulation data is GONE** - `run_events` table deleted
2. **Existing simulations show empty results** - no `latest_events` data  
3. **Frontend must test with NEW simulations only**
4. **Any direct database queries to `run_events` will fail**

### What Still Works (API Interface):
- ✅ **All endpoint URLs unchanged** - Same routes, same HTTP methods
- ✅ **Same JSON response structure** - Field names preserved (`opinion`, `engaged`, etc.)
- ✅ **No new required parameters** - Existing API calls will work
- ✅ **Frontend code should run without crashes** - Just with empty historical data

### Interface Compatibility:
**YES** - Your existing frontend code should run without modification, just with no historical data to display.

### Migration Impact:
- **Data loss**: Complete loss of all previous debate history
- **Testing**: Must create new simulations to test frontend
- **Analytics**: Historical analytics will be empty