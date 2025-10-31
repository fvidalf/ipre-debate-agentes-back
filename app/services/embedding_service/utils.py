"""
Utility functions for the embedding service.

Contains helper functions for model setup and configuration.
"""

import os


def setup_onnx_model(
    model_id: str = "sentence-transformers/all-MiniLM-L6-v2",
    output_dir: str = "./onnx-model"
) -> None:
    """
    Setup ONNX model for local inference (run this once to export the model).
    
    Args:
        model_id: Sentence transformer model ID to export
        output_dir: Directory to save the ONNX model
    """
    try:
        from transformers import AutoTokenizer
        from optimum.onnxruntime import ORTModelForFeatureExtraction
    except ImportError:
        raise ImportError(
            "ONNX model setup requires transformers and optimum. "
            "Install with: pip install transformers optimum[onnxruntime]"
        )
    
    print(f"Exporting {model_id} to ONNX format...")
    
    # Export the model - this creates a lightweight ONNX version
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    onnx_model = ORTModelForFeatureExtraction.from_pretrained(model_id, export=True)
    
    os.makedirs(output_dir, exist_ok=True)
    onnx_model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    print(f"ONNX model exported to {output_dir}")
    print("Note: This model requires mean pooling in the encode() method for sentence embeddings.")


def get_embedding_config_from_env() -> dict:
    """
    Get embedding service configuration from environment variables.
    
    Returns:
        Configuration dictionary for EmbeddingProviderFactory
    """
    provider_type = os.getenv("EMBEDDING_PROVIDER", "huggingface").lower()
    
    base_config = {
        "cache_config": {
            "capacity": int(os.getenv("EMBEDDING_CACHE_CAPACITY", "10000")),
            "ttl_seconds": int(os.getenv("EMBEDDING_CACHE_TTL", "3600"))
        }
    }
    
    # Provider-specific configuration
    if provider_type == "huggingface":
        base_config.update({
            "model": os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
            "api_key": os.getenv("HF_TOKEN"),
            "batch_size": int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
        })
    elif provider_type == "openrouter":
        base_config.update({
            "model_name": os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small"),
            "api_key": os.getenv("OPENROUTER_API_KEY")
        })
    elif provider_type == "onnx":
        base_config.update({
            "model_dir": os.getenv("ONNX_MODEL_DIR", "./onnx-model")
        })
    
    return provider_type, base_config