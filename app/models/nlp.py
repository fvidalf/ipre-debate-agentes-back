from typing import Tuple, Iterable
import numpy as np
from sentence_transformers import SentenceTransformer
from peft import PeftModel


class StanceAwareSBERT:
    def __init__(self, sbert: SentenceTransformer):
        self._sbert = sbert

    def __del__(self):
        """Cleanup resources on object deletion"""
        try:
            if hasattr(self, '_sbert') and self._sbert is not None:
                # Clean up the model
                if hasattr(self._sbert, '_modules'):
                    del self._sbert._modules
                del self._sbert
        except Exception:
            pass  # Ignore cleanup errors

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        a_norm = a / (np.linalg.norm(a) + 1e-12)
        b_norm = b / (np.linalg.norm(b) + 1e-12)
        return float(np.dot(a_norm, b_norm))

    def encode(self, sentences: Iterable[str]) -> np.ndarray:
        # Accepts str or list[str]; always returns 2D np.ndarray
        if isinstance(sentences, str):
            sentences = [sentences]
        return np.asarray(self._sbert.encode(list(sentences), convert_to_numpy=True))

    def text_similarity_score(self, text1: str, text2: str) -> float:
        embd1 = self.encode(text1)[0]
        embd2 = self.encode(text2)[0]
        return self.similarity(embd1, embd2)

    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return self._cosine_similarity(a, b)


def load_stance_aware_sbert(
    base_model: str = "sentence-transformers/all-mpnet-base-v2",
    peft_adapter: str = "vahidthegreat/StanceAware-SBERT"
) -> StanceAwareSBERT:
    """
    Load the base SBERT and attach the PEFT adapter once at process startup.
    """
    sbert = SentenceTransformer(base_model)
    # Attach PEFT adapter to the first module (the Transformer)
    sbert[0].auto_model = PeftModel.from_pretrained(sbert[0].auto_model, peft_adapter)
    return StanceAwareSBERT(sbert)
