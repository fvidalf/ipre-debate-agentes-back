import os
from typing import Iterable, Optional
import numpy as np
import dspy
from abc import ABC, abstractmethod


class BaseEncoder(ABC):
    """Abstract base class for all embedding encoders"""
    
    @abstractmethod
    def encode(self, sentences: Iterable[str]) -> np.ndarray:
        """Encode sentences into embeddings"""
        pass


class OpenRouterEncoder(BaseEncoder):
    """OpenRouter embedding encoder using DSPy"""
    
    def __init__(self, model_name: str = "openai/text-embedding-3-small", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")
        
        # Configure DSPy embedder for OpenRouter
        self.embedder = dspy.Embedder(
            model=self.model_name,
            api_base="https://openrouter.ai/api/v1",
            api_key=self.api_key
        )
    
    def encode(self, sentences: Iterable[str]) -> np.ndarray:
        if isinstance(sentences, str):
            sentences = [sentences]
        
        embeddings = self.embedder(list(sentences))
        return np.asarray(embeddings, dtype=np.float32)


class ONNXMiniLMEncoder(BaseEncoder):
    """ONNX-optimized sentence encoder for lightweight inference"""
    
    def __init__(self, model_dir: str = "./onnx-model"):
        try:
            import onnxruntime as ort
            from transformers import AutoTokenizer
        except ImportError:
            raise ImportError("Please install onnxruntime and transformers: pip install onnxruntime transformers")
        
        self.model_dir = model_dir
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.session = ort.InferenceSession(
            os.path.join(model_dir, "model.onnx"),
            providers=["CPUExecutionProvider"]
        )
    
    def encode(self, sentences: Iterable[str]) -> np.ndarray:
        if isinstance(sentences, str):
            sentences = [sentences]
        
        enc = self.tokenizer(
            list(sentences), 
            return_tensors="np", 
            padding=True, 
            truncation=True, 
            max_length=256
        )
        
        # Prepare inputs for ONNX model - include all required inputs
        input_feed = {}
        for input_node in self.session.get_inputs():
            input_name = input_node.name
            if input_name in enc:
                input_feed[input_name] = enc[input_name]
        
        # Run inference
        outputs = self.session.run(None, input_feed)[0]
        
        # Apply mean pooling using attention mask
        attention_mask = enc["attention_mask"]
        
        # Mean pooling: sum embeddings and divide by attention mask sum
        masked_embeddings = outputs * np.expand_dims(attention_mask, axis=-1)
        summed = np.sum(masked_embeddings, axis=1)
        counts = np.sum(attention_mask, axis=1, keepdims=True)
        counts = np.maximum(counts, 1)  # Avoid division by zero
        
        mean_pooled = summed / counts
        return mean_pooled.astype(np.float32)


class SentenceEmbedder:
    """Unified sentence embedder with multiple backend options"""
    
    def __init__(self, model_type: str = "openrouter", **kwargs):
        self.model_type = model_type
        
        if model_type == "openrouter":
            self.encoder = OpenRouterEncoder(**kwargs)
        elif model_type == "onnx_minilm":
            self.encoder = ONNXMiniLMEncoder(**kwargs)
        else:
            raise ValueError(f"Unsupported model type: {model_type}. Supported types: 'openrouter', 'onnx_minilm'")
    
    def __del__(self):
        """Cleanup resources on object deletion"""
        try:
            if hasattr(self, 'encoder'):
                del self.encoder
        except Exception:
            pass  # Ignore cleanup errors
    
    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        a_norm = a / (np.linalg.norm(a) + 1e-12)
        b_norm = b / (np.linalg.norm(b) + 1e-12)
        return float(np.dot(a_norm, b_norm))
    
    def encode(self, sentences: Iterable[str]) -> np.ndarray:
        """Encode sentences into embeddings
        
        Args:
            sentences: String or list of strings to encode
            
        Returns:
            2D numpy array of embeddings
        """
        if isinstance(sentences, str):
            sentences = [sentences]
        return self.encoder.encode(sentences)
    
    def text_similarity_score(self, text1: str, text2: str) -> float:
        """Calculate similarity score between two texts"""
        embd1 = self.encode(text1)[0]
        embd2 = self.encode(text2)[0]
        return self.similarity(embd1, embd2)
    
    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate similarity between two embedding vectors"""
        return self._cosine_similarity(a, b)


def create_sentence_embedder(
    model_type: str = "openrouter",
    **kwargs
) -> SentenceEmbedder:
    """
    Factory function to create a sentence embedder
    
    Args:
        model_type: Type of model ('openrouter' or 'onnx_minilm')
        **kwargs: Additional arguments for the specific encoder
        
    Returns:
        SentenceEmbedder instance
    """
    return SentenceEmbedder(model_type=model_type, **kwargs)


def setup_onnx_model(
    model_id: str = "sentence-transformers/all-MiniLM-L6-v2",
    output_dir: str = "./onnx-model"
) -> None:
    """
    Setup ONNX model for local inference (run this once to export the model)
    
    Args:
        model_id: Sentence transformer model ID to export
        output_dir: Directory to save the ONNX model
    """
    try:
        from transformers import AutoTokenizer
        from optimum.onnxruntime import ORTModelForFeatureExtraction
    except ImportError:
        raise ImportError("Please install transformers and optimum: pip install transformers optimum[onnxruntime]")
    
    print(f"Exporting {model_id} to ONNX format...")
    
    # Export the model - this creates a lightweight ONNX version
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    onnx_model = ORTModelForFeatureExtraction.from_pretrained(model_id, export=True)
    
    os.makedirs(output_dir, exist_ok=True)
    onnx_model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    
    print(f"ONNX model exported to {output_dir}")
    print("Note: This model requires mean pooling in the encode() method for sentence embeddings.")


# Backward compatibility - create an alias
StanceAwareSBERT = SentenceEmbedder  # For backward compatibility

def load_stance_aware_sbert(**kwargs) -> SentenceEmbedder:
    """Backward compatibility function"""
    return create_sentence_embedder(**kwargs)
