# Embedding Models Configuration

The debate simulation system now supports multiple embedding models for sentence similarity calculations. You can choose between different models based on your performance and quality requirements.

## Available Embedding Models

### 1. OpenRouter Embeddings (Default)
- **Model Type**: `"openrouter"`
- **Description**: Uses OpenAI's text-embedding-3-small model via OpenRouter API
- **Advantages**: High quality embeddings, no local resource usage
- **Requirements**: OpenRouter API key

```json
{
  "embedding_model": "openrouter",
  "embedding_config": {
    "model_name": "openai/text-embedding-3-small"
  }
}
```

### 2. Local ONNX MiniLM
- **Model Type**: `"onnx_minilm"`  
- **Description**: Lightweight local inference using ONNX runtime
- **Advantages**: No API costs, fast inference, privacy-preserving
- **Requirements**: Model setup (see setup instructions below)

```json
{
  "embedding_model": "onnx_minilm",
  "embedding_config": {
    "model_dir": "./onnx-model"
  }
}
```

## Setup Instructions

### OpenRouter Setup
1. Get an API key from [OpenRouter](https://openrouter.ai/)
2. Set the environment variable:
   ```bash
   export OPENROUTER_API_KEY="your-api-key-here"
   ```

### ONNX Model Setup
1. Install required dependencies:
   ```bash
   pip install transformers optimum[onnxruntime] onnxruntime
   ```

2. Run the setup script:
   ```bash
   python scripts/setup_onnx_model.py
   ```

This will download and convert the MiniLM model to ONNX format in the `./onnx-model` directory.

## API Usage Examples

### Creating a simulation with OpenRouter embeddings:
```bash
curl -X POST "http://localhost:8000/simulations" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Should AI be regulated?",
    "profiles": ["conservative", "liberal"],
    "agent_names": ["Alice", "Bob"],
    "embedding_model": "openrouter",
    "embedding_config": {
      "model_name": "openai/text-embedding-3-small"
    }
  }'
```

### Creating a simulation with local ONNX model:
```bash
curl -X POST "http://localhost:8000/simulations" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Should AI be regulated?",
    "profiles": ["conservative", "liberal"], 
    "agent_names": ["Alice", "Bob"],
    "embedding_model": "onnx_minilm",
    "embedding_config": {
      "model_dir": "./onnx-model"
    }
  }'
```

## Performance Comparison

| Model | Speed | Quality | Resource Usage | API Cost |
|-------|--------|---------|----------------|----------|
| OpenRouter | Medium | High | Low (API calls) | Yes |
| ONNX MiniLM | Fast | Good | Low (CPU only) | No |

## Migration from Previous Version

The system maintains backward compatibility. If no `embedding_model` is specified, it defaults to "openrouter". The old `StanceAwareSBERT` class has been removed due to its heavy resource requirements.

## Troubleshooting

### OpenRouter Issues
- Verify your API key is set correctly
- Check your OpenRouter account has sufficient credits
- Ensure network connectivity to openrouter.ai

### ONNX Model Issues  
- Make sure the setup script ran successfully
- Verify the `./onnx-model` directory contains the model files
- Check that onnxruntime is installed correctly

### Memory Issues
- ONNX models use minimal memory compared to the previous SBERT approach
- Each simulation creates its own embedder instance for isolation
