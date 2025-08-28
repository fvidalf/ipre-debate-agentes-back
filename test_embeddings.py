#!/usr/bin/env python3
"""
Test script for the new embedding system.
This script tests the basic functionality without requiring a full server setup.
"""

import os
import sys
import tempfile

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))

def test_openrouter_embedder():
    """Test OpenRouter embedder (requires API key)"""
    print("Testing OpenRouter embedder...")
    
    try:
        from app.models.nlp import create_sentence_embedder
        
        # Check if API key is available
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("⚠️  OpenRouter API key not found. Skipping OpenRouter test.")
            return
        
        embedder = create_sentence_embedder(
            model_type="openrouter",
            model_name="openai/text-embedding-3-small"
        )
        
        # Test encoding
        sentences = ["AI is beneficial", "AI is harmful", "Technology helps society"]
        embeddings = embedder.encode(sentences)
        
        print(f"✅ OpenRouter embedder working. Embeddings shape: {embeddings.shape}")
        
        # Test similarity
        similarity = embedder.text_similarity_score("AI is beneficial", "AI is helpful")
        print(f"✅ Similarity calculation working. Score: {similarity:.3f}")
        
    except ImportError as e:
        print(f"⚠️  Missing dependencies for OpenRouter: {e}")
    except Exception as e:
        print(f"❌ OpenRouter test failed: {e}")


def test_onnx_embedder():
    """Test ONNX embedder (requires model setup)"""
    print("\nTesting ONNX embedder...")
    
    try:
        from models.nlp import create_sentence_embedder
        
        # Check if ONNX model exists
        model_dir = "./onnx-model"
        if not os.path.exists(os.path.join(model_dir, "model.onnx")):
            print("⚠️  ONNX model not found. Run 'python scripts/setup_onnx_model.py' first.")
            return
        
        embedder = create_sentence_embedder(
            model_type="onnx_minilm",
            model_dir=model_dir
        )
        
        # Test encoding
        sentences = ["AI is beneficial", "AI is harmful", "Technology helps society"]
        embeddings = embedder.encode(sentences)
        
        print(f"✅ ONNX embedder working. Embeddings shape: {embeddings.shape}")
        
        # Test similarity
        similarity = embedder.text_similarity_score("AI is beneficial", "AI is helpful")
        print(f"✅ Similarity calculation working. Score: {similarity:.3f}")
        
    except ImportError as e:
        print(f"⚠️  Missing dependencies for ONNX: {e}")
    except Exception as e:
        print(f"❌ ONNX test failed: {e}")


def test_backward_compatibility():
    """Test backward compatibility with old interface"""
    print("\nTesting backward compatibility...")
    
    try:
        from models.nlp import load_stance_aware_sbert, StanceAwareSBERT
        
        # Test that old function exists and works
        embedder = load_stance_aware_sbert()
        print("✅ load_stance_aware_sbert() function works")
        
        # Test that it returns compatible interface
        sentences = ["Test sentence 1", "Test sentence 2"]
        if hasattr(embedder, 'encode') and hasattr(embedder, 'text_similarity_score'):
            print("✅ Backward compatible interface maintained")
        else:
            print("❌ Backward compatible interface missing")
            
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")


def main():
    """Run all tests"""
    print("🧪 Testing new embedding system...")
    print("=" * 50)
    
    test_openrouter_embedder()
    test_onnx_embedder() 
    test_backward_compatibility()
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")
    print("\nNext steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Set OpenRouter API key: export OPENROUTER_API_KEY='your-key'")
    print("3. Setup ONNX model: python scripts/setup_onnx_model.py")
    print("4. Start the server: uvicorn app.main:app --reload")


if __name__ == "__main__":
    main()
