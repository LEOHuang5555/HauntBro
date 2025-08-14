"""
RAG (Retrieval-Augmented Generation) Engine
Combines semantic search with conversational AI for enhanced story discovery
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import json
import logging
import asyncio

# Add project root to path  
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from etl.models.embedding_manager import EmbeddingManager
from etl.config.config import CONFIG
from infrastructure.database.models import BronzeStory, SilverStory, SilverStoryChunks

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    RAG Engine for conversational story discovery
    Combines semantic search with AI-powered response generation
    """
    
    def __init__(self):
        self.embedding_manager = None
        self.openai_client = None
        self.is_initialized = False
        
        # RAG configuration
        self.max_context_chunks = 5
        self.similarity_threshold = 0.7
        self.max_response_tokens = 500
        
    async def initialize(self) -> bool:
        """Initialize the RAG engine"""
        try:
            # Initialize embedding manager
            self.embedding_manager = EmbeddingManager()
            await self.embedding_manager.initialize()
            
            # Initialize OpenAI client for response generation
            from openai import OpenAI
            openai_config = CONFIG["openai"]
            
            if openai_config.api_key:
                self.openai_client = OpenAI(api_key=openai_config.api_key)
                self.is_initialized = True
                logger.info("RAG Engine initialized successfully")
                return True
            else:
                logger.warning("OpenAI API key not found - RAG responses will be disabled")
                return False
                
        except Exception as e:
            logger.error(f"RAG Engine initialization failed: {e}")
            return False
    
    async def query(
        self,
        question: str,
        db_session,
        language: str = "auto",
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Process a RAG query with conversational context
        
        Args:
            question: User's question/query
            db_session: Database session
            language: Language hint
            conversation_history: Previous conversation turns
            
        Returns:
            RAG response with answer and source stories
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            if not self.is_initialized:
                await self.initialize()
            
            # Step 1: Retrieve relevant story chunks
            relevant_chunks = await self._retrieve_relevant_chunks(
                question, db_session, language
            )
            
            if not relevant_chunks:
                return {
                    "answer": "I couldn't find any relevant stories to answer your question. Try rephrasing or asking about different horror themes.",
                    "sources": [],
                    "confidence": 0.0,
                    "query_metadata": {
                        "execution_time_ms": 0,
                        "chunks_retrieved": 0
                    }
                }
            
            # Step 2: Generate AI response using retrieved context
            if self.openai_client:
                answer = await self._generate_response(
                    question, relevant_chunks, conversation_history
                )
                confidence = self._calculate_confidence(relevant_chunks)
            else:
                # Fallback: Create a simple response from chunk content
                answer = await self._create_fallback_response(question, relevant_chunks)
                confidence = 0.6
            
            # Step 3: Format sources
            sources = await self._format_sources(relevant_chunks, db_session)
            
            execution_time_ms = int(
                (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )
            
            return {
                "answer": answer,
                "sources": sources,
                "confidence": confidence,
                "query_metadata": {
                    "execution_time_ms": execution_time_ms,
                    "chunks_retrieved": len(relevant_chunks),
                    "has_ai_response": self.openai_client is not None
                }
            }
            
        except Exception as e:
            logger.error(f"RAG query error: {e}")
            return {
                "answer": f"Sorry, I encountered an error while processing your question: {str(e)}",
                "sources": [],
                "confidence": 0.0,
                "query_metadata": {
                    "execution_time_ms": int(
                        (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                    ),
                    "chunks_retrieved": 0,
                    "error": str(e)
                }
            }
    
    async def _retrieve_relevant_chunks(
        self, 
        question: str, 
        db_session,
        language: str
    ) -> List[Tuple[SilverStoryChunks, float]]:
        """Retrieve relevant story chunks using semantic search"""
        try:
            if not self.embedding_manager:
                return []
            
            # Generate question embedding
            embedding_result = await self.embedding_manager.generate_embeddings(
                text=question,
                search_text=question,
                language=language,
                strategy="speed_optimized"
            )
            
            if not embedding_result.success or not embedding_result.search_embedding:
                logger.warning("Failed to generate question embedding")
                return []
            
            query_embedding = embedding_result.search_embedding
            
            # Get all chunks with embeddings
            from sqlalchemy import select
            stmt = (
                select(SilverStoryChunks)
                .join(BronzeStory, SilverStoryChunks.story_id == BronzeStory.id)
                .where(SilverStoryChunks.search_embedding.isnot(None))
                .limit(1000)  # Limit for performance
            )
            
            chunks = db_session.execute(stmt).scalars().all()
            
            if not chunks:
                return []
            
            # Calculate similarities
            similarities = []
            for chunk in chunks:
                try:
                    chunk_embedding = json.loads(chunk.search_embedding)
                    similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                    
                    if similarity >= self.similarity_threshold:
                        similarities.append((chunk, similarity))
                        
                except (json.JSONDecodeError, TypeError):
                    continue
            
            # Sort by similarity and return top chunks
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:self.max_context_chunks]
            
        except Exception as e:
            logger.error(f"Error retrieving relevant chunks: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import numpy as np
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            return float(dot_product / (norm1 * norm2))
        except Exception:
            return 0.0
    
    async def _generate_response(
        self,
        question: str,
        relevant_chunks: List[Tuple[SilverStoryChunks, float]],
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """Generate AI response using OpenAI"""
        try:
            # Prepare context from relevant chunks
            context_parts = []
            for chunk, similarity in relevant_chunks:
                context_parts.append(f"[Story Excerpt - Similarity: {similarity:.2f}]\n{chunk.content}")
            
            context = "\n\n".join(context_parts)
            
            # Build conversation messages
            messages = [
                {
                    "role": "system",
                    "content": """You are a knowledgeable horror story enthusiast who helps users discover and understand ghost stories and horror content. 

Use the provided story excerpts to answer the user's question. Be engaging, insightful, and helpful. If the excerpts don't contain enough information to fully answer the question, acknowledge this and provide what information you can.

Guidelines:
- Be conversational and engaging
- Reference specific details from the story excerpts when possible
- If asked about themes, explain them clearly
- For recommendations, explain why the stories might appeal to the user
- Keep responses concise but informative (max 3 paragraphs)
- Always be respectful of the horror genre and its themes"""
                }
            ]
            
            # Add conversation history if provided
            if conversation_history:
                for turn in conversation_history[-3:]:  # Last 3 turns for context
                    messages.append({
                        "role": "user" if turn.get("type") == "question" else "assistant",
                        "content": turn.get("content", "")
                    })
            
            # Add current question with context
            user_message = f"""Question: {question}

Relevant Story Excerpts:
{context}

Please provide a helpful response based on the story excerpts above."""

            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # Generate response
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=self.max_response_tokens,
                temperature=0.7
            )
            
            if response.choices:
                return response.choices[0].message.content.strip()
            else:
                return await self._create_fallback_response(question, relevant_chunks)
                
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return await self._create_fallback_response(question, relevant_chunks)
    
    async def _create_fallback_response(
        self, 
        question: str, 
        relevant_chunks: List[Tuple[SilverStoryChunks, float]]
    ) -> str:
        """Create a fallback response when AI generation fails"""
        if not relevant_chunks:
            return "I couldn't find relevant stories to answer your question."
        
        # Create a simple response based on chunk content
        story_count = len(set(chunk.story_id for chunk, _ in relevant_chunks))
        
        response_parts = [
            f"I found {story_count} relevant {'story' if story_count == 1 else 'stories'} related to your question."
        ]
        
        # Add top chunk content as context
        top_chunk, similarity = relevant_chunks[0]
        if top_chunk.content:
            preview = top_chunk.content[:200] + "..." if len(top_chunk.content) > 200 else top_chunk.content
            response_parts.append(f"Here's an excerpt from the most relevant story: \"{preview}\"")
        
        return " ".join(response_parts)
    
    def _calculate_confidence(self, relevant_chunks: List[Tuple[SilverStoryChunks, float]]) -> float:
        """Calculate confidence score based on retrieval quality"""
        if not relevant_chunks:
            return 0.0
        
        # Use average similarity as confidence score
        avg_similarity = sum(similarity for _, similarity in relevant_chunks) / len(relevant_chunks)
        
        # Boost confidence if we have multiple high-quality chunks
        chunk_count_factor = min(1.0, len(relevant_chunks) / self.max_context_chunks)
        
        return min(1.0, avg_similarity * 0.8 + chunk_count_factor * 0.2)
    
    async def _format_sources(
        self, 
        relevant_chunks: List[Tuple[SilverStoryChunks, float]],
        db_session
    ) -> List[Dict[str, Any]]:
        """Format source stories for the response"""
        sources = []
        seen_stories = set()
        
        for chunk, similarity in relevant_chunks:
            story_id = chunk.story_id
            
            if story_id in seen_stories:
                continue
                
            seen_stories.add(story_id)
            
            try:
                # Get bronze story details
                from sqlalchemy import select
                bronze_stmt = select(BronzeStory).where(BronzeStory.id == story_id)
                bronze_story = db_session.execute(bronze_stmt).scalar_one_or_none()
                
                if bronze_story:
                    source = {
                        "story_id": str(story_id),
                        "title": bronze_story.title or "Untitled",
                        "author": bronze_story.author,
                        "source": bronze_story.source,
                        "post_date": bronze_story.post_date.isoformat() if bronze_story.post_date else None,
                        "similarity_score": round(similarity, 3),
                        "excerpt": chunk.content[:150] + "..." if chunk.content and len(chunk.content) > 150 else chunk.content
                    }
                    sources.append(source)
                    
            except Exception as e:
                logger.warning(f"Error formatting source {story_id}: {e}")
                continue
        
        return sources
    
    async def suggest_follow_up_questions(
        self, 
        original_question: str, 
        sources: List[Dict[str, Any]]
    ) -> List[str]:
        """Suggest follow-up questions based on the search results"""
        if not sources:
            return []
        
        # Simple rule-based suggestions based on content analysis
        suggestions = []
        
        # Analyze story themes and suggest related questions
        if any("ghost" in (source.get("title", "") + source.get("excerpt", "")).lower() for source in sources):
            suggestions.extend([
                "What are common characteristics of ghost stories?",
                "Can you recommend similar ghost stories?"
            ])
        
        if any("haunted" in (source.get("title", "") + source.get("excerpt", "")).lower() for source in sources):
            suggestions.extend([
                "What makes a place haunted in these stories?",
                "Are there patterns in haunted house stories?"
            ])
        
        # Limit suggestions
        return suggestions[:3]


# Singleton instance
_rag_engine = None

async def get_rag_engine() -> RAGEngine:
    """Get or create the RAG engine singleton"""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
        await _rag_engine.initialize()
    return _rag_engine