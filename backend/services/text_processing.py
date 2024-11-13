# services/text_processing.py
from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np

class TextProcessingService:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def extract_relevant_text(self, full_text: str, query: str, max_chunks: int = 3) -> str:
        """Extract most relevant text chunks based on query"""
        # Split text into chunks
        chunks = [chunk.strip() for chunk in full_text.split('\n\n') if chunk.strip()]
        
        if not chunks:
            return ""

        try:
            # Get embeddings
            query_embedding = self.model.encode(query)
            chunk_embeddings = self.model.encode(chunks)

            # Calculate similarities
            similarities = np.dot(chunk_embeddings, query_embedding)
            
            # Get top chunks
            top_indices = np.argsort(similarities)[-max_chunks:]
            relevant_chunks = [chunks[i] for i in top_indices]
            
            return " ".join(relevant_chunks)

        except Exception as e:
            print(f"Error extracting relevant text: {e}")
            return ""
    def rank_contexts(self, contexts: List[str], query: str) -> List[str]:
        # Example implementation for ranking
        embeddings = self.model.encode(contexts)
        query_embedding = self.model.encode(query)
        scores = np.dot(embeddings, query_embedding)
        ranked_indices = np.argsort(scores)[::-1]
        return [contexts[i] for i in ranked_indices]

# Create instance for import
text_processor = TextProcessingService()
extract_relevant_text = text_processor.extract_relevant_text