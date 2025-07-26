from typing import List, Tuple
from sentence_transformers import SentenceTransformer
import openai
import asyncio
from etl.config.config import CONFIG

class EmbeddingGenerator:
    """Generate embeddings for chunks using both local and OpenAI models"""
    
    def __init__(self, use_openai: bool = True):
        self.use_openai = use_openai
        self.openai_config = CONFIG["openai"]
        
        if self.use_openai:
            # Initialize OpenAI client
            openai.api_key = self.openai_config.api_key
            self.client = openai.OpenAI()
        else:
            # Initialize local sentence transformer
            self.sentence_model = SentenceTransformer(CONFIG["chunking"].embedding_model)
        
    def generate_embeddings(self, chunk_text: str, chunk_context: str) -> Tuple[List[float], List[float]]:
        """Generate both content and search embeddings"""
        try:
            if self.use_openai:
                return self._generate_openai_embeddings(chunk_text, chunk_context)
            else:
                return self._generate_local_embeddings(chunk_text, chunk_context)
                
        except Exception as e:
            print(f"Embedding generation failed: {e}")
            return [], []
    
    def _generate_openai_embeddings(self, chunk_text: str, chunk_context: str) -> Tuple[List[float], List[float]]:
        """Generate embeddings using OpenAI API"""
        try:
            # Generate embeddings for both texts
            search_response = self.client.embeddings.create(
                input=chunk_text,
                model=self.openai_config.embedding_model
            )
            
            content_response = self.client.embeddings.create(
                input=chunk_context,
                model=self.openai_config.embedding_model
            )
            
            search_embedding = search_response.data[0].embedding
            content_embedding = content_response.data[0].embedding
            
            return content_embedding, search_embedding
            
        except Exception as e:
            print(f"OpenAI embedding generation failed: {e}")
            # Fallback to local embeddings
            return self._generate_local_embeddings(chunk_text, chunk_context)
    
    def _generate_local_embeddings(self, chunk_text: str, chunk_context: str) -> Tuple[List[float], List[float]]:
        """Generate embeddings using local sentence transformer"""
        # Initialize model if not using OpenAI
        if not hasattr(self, 'sentence_model'):
            self.sentence_model = SentenceTransformer(CONFIG["chunking"].embedding_model)
        
        # Search embedding - optimized for queries
        search_embedding = self.sentence_model.encode(chunk_text).tolist()
        
        # Content embedding - richer context
        content_embedding = self.sentence_model.encode(chunk_context).tolist()
        
        return content_embedding, search_embedding
    
    async def generate_embeddings_async(self, chunk_text: str, chunk_context: str) -> Tuple[List[float], List[float]]:
        """Async version for better performance in pipeline"""
        if self.use_openai:
            # Run OpenAI API calls in thread pool
            return await asyncio.to_thread(self._generate_openai_embeddings, chunk_text, chunk_context)
        else:
            # Run local model in thread pool to avoid blocking
            return await asyncio.to_thread(self._generate_local_embeddings, chunk_text, chunk_context)
    
    def estimate_cost(self, num_chunks: int, avg_tokens_per_chunk: int = 100) -> float:
        """Estimate OpenAI embedding cost"""
        if not self.use_openai:
            return 0.0  # Local embeddings are free
        
        # OpenAI text-embedding-3-small pricing: $0.00002 per 1K tokens
        total_tokens = num_chunks * avg_tokens_per_chunk * 2  # 2 embeddings per chunk
        cost_per_1k_tokens = 0.00002
        estimated_cost = (total_tokens / 1000) * cost_per_1k_tokens
        
        return round(estimated_cost, 4)