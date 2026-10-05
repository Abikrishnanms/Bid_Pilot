from sentence_transformers import SentenceTransformer
import os
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        # We use a fast, lightweight model suitable for 384 dimensions by default
        # all-MiniLM-L6-v2 outputs 384 dimensional vectors
        model_name = os.getenv("EMBEDDING_PROVIDER", "all-MiniLM-L6-v2")
        
        # In a real microservice, we'd wrap this with Mock logic if needed
        if model_name == "sentence-transformers":
            model_name = "all-MiniLM-L6-v2"
            
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)

    def get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding for a piece of text.
        Returns a list of floats (length 384).
        """
        embedding = self.model.encode(text)
        return embedding.tolist()

    def embed_chunks(self, texts: list[str]) -> list[list[float]]:
        """
        Batch generate embeddings.
        """
        embeddings = self.model.encode(texts)
        return [emb.tolist() for emb in embeddings]
