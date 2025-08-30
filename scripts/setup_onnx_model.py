#!/usr/bin/env python3
"""
Setup script to export and prepare ONNX model for local inference.
Run this once to set up the ONNX model before using the 'onnx_minilm' embedding option.
"""

import os
import sys

# Handle both Docker and local execution paths
if os.path.exists('/app/app'):
    # Docker context
    sys.path.insert(0, '/app')
    from app.classes.nlp import setup_onnx_model
else:
    # Local context
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.classes.nlp import setup_onnx_model


def main():
    """Main setup function"""
    print("Setting up ONNX MiniLM model for local inference...")
    
    # Default configuration - adjust paths for Docker if needed
    model_id = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Determine output directory based on environment
    if os.path.exists('/app'):
        # Docker context
        output_dir = "/app/onnx-model"
    else:
        # Local context
        output_dir = "./onnx-model"
    
    try:
        setup_onnx_model(model_id=model_id, output_dir=output_dir)
        print("\n✅ ONNX model setup complete!")
        print(f"Model exported to: {os.path.abspath(output_dir)}")
        print("\nYou can now use embedding_model='onnx_minilm' in your API requests.")
        
    except ImportError as e:
        print(f"\n❌ Missing dependencies: {e}")
        print("Please install required packages:")
        print("pip install transformers optimum[onnxruntime] onnxruntime")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
