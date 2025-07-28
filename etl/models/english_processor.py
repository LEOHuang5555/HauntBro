"""
English Text Processor - LLaMA Integration  
Handles English ghost story processing with LLaMA models
"""

import asyncio
import re
import json
import requests
from typing import List, Dict, Optional, Tuple, Any, Literal
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys
import time
from pydantic import BaseModel, Field, field_validator

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from etl.config.config import CONFIG, ModelConfig, ChunkingConfig

# Pydantic models for structured parsing
class GPTChunk(BaseModel):
    """Enhanced chunk model with strict validation for English text"""
    text: str = Field(
        description="Chunk text content, not empty"
    )
    type: Literal[
        "opening",
        "development", 
        "body",
        "climax",
        "ending",
        "transition",
        "dialogue",
        "description"
    ] = Field(
        default="body",
        description="Narrative type of the chunk"
    )
    order: int = Field(
        description="Sequential order of the chunk"
    )
    keywords: List[str] = Field(
        default_factory=list,
        min_items=0,
        max_items=10,
        description="Key terms or phrases from the chunk"
    )
    confidence_score: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="LLM confidence in chunking decision"
    )
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        
        # Check for reasonable English text content
        english_chars = len(re.findall(r'[a-zA-Z]', v))
        if english_chars < len(v) * 0.5:  # At least 50% English characters
            raise ValueError("Text must contain substantial English content")
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', v.strip())
        return cleaned
    
    @field_validator('keywords')
    @classmethod
    def validate_keywords(cls, v: List[str]) -> List[str]:
        if not v:
            return []
        
        valid_keywords = []
        for keyword in v:
            if isinstance(keyword, str) and keyword.strip():
                # Clean and validate keyword
                clean_keyword = keyword.strip()
                if (len(clean_keyword) >= 1 and 
                    len(clean_keyword) <= 25 and
                    not clean_keyword.isspace()):
                    valid_keywords.append(clean_keyword)
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(valid_keywords))

class GPTChunkResponse(BaseModel):
    chunks: List[GPTChunk]

class NarrativeElementsResponse(BaseModel):
    elements: List[str]

class HorrorIndicatorsResponse(BaseModel):
    horror_indicators: List[str]

class KeywordsResponse(BaseModel):
    keywords: List[str]

# English text processing imports
try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


@dataclass
class EnglishChunk:
    """English text chunk with semantic context"""
    chunk_id: str
    original_text: str
    normalized_text: str  # Renamed from processed_text for consistency
    chunk_order: int
    character_count: int  # Added for consistency with Chinese processor
    word_count: int
    sentence_count: int
    semantic_keywords: List[str]
    dialogue_ratio: float  # Percentage of text that is dialogue
    processing_metadata: Dict[str, Any]
    chunk_type: Literal[
        "opening",
        "development",
        "body",
        "climax",
        "ending",
        "transition",
        "dialogue",
        "description"
    ] = "body"  # Standardized chunk types


@dataclass
class ProcessingResult:
    """Result of English text processing"""
    success: bool
    chunks: List[EnglishChunk]
    processing_time_ms: int
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None


class EnglishProcessor:
    """
    GPT-4o-mini-powered English text processor for ghost stories
    Handles narrative structure preservation, dialogue detection, and semantic chunking
    """
    
    def _extract_json_from_response(self, response_text: str) -> Optional[Dict]:
        """Extract JSON from API response, handling extra text"""
        # Try parsing the response as-is first
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            pass
        
        # Look for JSON content between markers
        import re
        json_patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Find any JSON object
            r'```json\s*(\{.*?\})\s*```',  # JSON in code blocks
            r'```\s*(\{.*?\})\s*```'  # JSON in generic code blocks
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, response_text, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def __init__(self, cache_dir: str = "./models"):
        """Initialize English processor with Ollama LLaMA model"""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Model configuration
        self.model_config: ModelConfig = CONFIG["model"]
        self.chunking_config: ChunkingConfig = CONFIG["chunking"]  
        
        # OpenAI configuration
        self.openai_config = CONFIG["openai"]
        self.model_name = "gpt-4o-mini"  # Cost-effective and reliable
        self.is_initialized = False
        self.openai_client = None
        
        # English processing setup
        self._setup_english_processors()
        
        # Processing statistics
        self.processing_stats = {
            'total_processed': 0,
            'total_chunks': 0,
            'avg_processing_time': 0.0,
            'errors': 0
        }
        
        # Rate limiting for OpenAI API (500 RPM limit)
        self.last_api_call = 0
        self.min_call_interval = 0.12  # 120ms between calls for 500 RPM
    
    async def _rate_limit_openai_call(self):
        """Ensure we don't exceed OpenAI rate limits"""
        current_time = time.time()
        elapsed = current_time - self.last_api_call
        
        if elapsed < self.min_call_interval:
            wait_time = self.min_call_interval - elapsed
            print(f"⏱️  Rate limiting: waiting {wait_time:.1f}s before OpenAI call")
            await asyncio.sleep(wait_time)
        
        self.last_api_call = time.time()
    
    def _setup_english_processors(self):
        """Setup English text processing tools"""
        try:
            # Download required NLTK data
            if NLTK_AVAILABLE:
                nltk.download('punkt', quiet=True)
                nltk.download('stopwords', quiet=True)
                nltk.download('averaged_perceptron_tagger', quiet=True)
                self.stop_words = set(stopwords.words('english'))
                print("✅ English text processing tools initialized")
        except Exception as e:
            print(f"⚠️  NLTK setup failed: {e}")
            self.stop_words = set()
    
    async def initialize(self) -> bool:
        """Initialize OpenAI GPT-4o-mini for English processing"""
        try:
            print("🚀 Initializing GPT-4o-mini for English processing...")
            
            # Import OpenAI client
            from openai import OpenAI
            
            # Check if API key is available
            if not self.openai_config.api_key:
                print("❌ OpenAI API key not found in configuration")
                return False
            
            # Initialize OpenAI client
            self.openai_client = OpenAI(api_key=self.openai_config.api_key)
            
            # Test model with a simple request
            test_response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.model_name,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5,
                temperature=0.3
            )
            
            if not test_response:
                print("❌ GPT-4o-mini test failed")
                return False
            
            self.is_initialized = True
            print(f"✅ GPT-4o-mini initialized successfully for English processing")
            return True
            
        except Exception as e:
            print(f"❌ GPT-4o-mini initialization failed: {e}")
            return False
    
    def normalize_english_text(self, text: str) -> str:
        """
        Normalize English text for consistent processing
        Handles formatting, encoding, and standardization
        """
        if not text:
            return ""
        
        try:
            # Basic text cleaning
            text = re.sub(r'\r\n|\r|\n', '\n', text)  # Normalize line endings
            text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
            text = re.sub(r'…', '...', text)  # Standardize ellipsis
            
            # Fix common Reddit formatting
            text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Remove bold markdown
            text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Remove italic markdown
            text = re.sub(r'^\s*&gt;', '>', text, flags=re.MULTILINE)  # Fix quotes
            
            # Clean up excessive punctuation
            text = re.sub(r'[.]{4,}', '...', text)  # Multiple dots to ellipsis
            text = re.sub(r'[!]{2,}', '!', text)  # Multiple exclamations
            text = re.sub(r'[?]{2,}', '?', text)  # Multiple questions
            
            # Remove Reddit-specific footers and edits
            text = re.sub(r'\n\s*---+\s*\n.*$', '', text, flags=re.DOTALL)
            text = re.sub(r'\n\s*Edit:.*$', '', text, flags=re.DOTALL)
            text = re.sub(r'\n\s*EDIT:.*$', '', text, flags=re.DOTALL)
            text = re.sub(r'\n\s*UPDATE:.*$', '', text, flags=re.DOTALL)
            
            return text.strip()
            
        except Exception as e:
            print(f"❌ Text normalization failed: {e}")
            return text  # Return original if normalization fails
    
    
    def calculate_dialogue_ratio(self, text: str) -> float:
        """Calculate percentage of text that is dialogue"""
        # Simple dialogue detection using quotes
        dialogue_chars = 0
        
        # Find text within quotes
        dialogue_matches = re.findall(r'"([^"]*)"', text)
        dialogue_chars += sum(len(match) for match in dialogue_matches)
        
        # Also check single quotes for dialogue
        single_quote_matches = re.findall(r"'([^']*)'", text)
        dialogue_chars += sum(len(match) for match in single_quote_matches)
        
        total_chars = len(text.replace(' ', ''))
        if total_chars == 0:
            return 0.0
        
        return min(1.0, dialogue_chars / total_chars)
    
    def extract_keywords_nltk(self, text: str) -> List[str]:
        """Extract keywords using LLM-powered extraction"""
        # Use LLaMA for keyword extraction if available
        if self.is_initialized:
            return asyncio.run(self._extract_keywords_llama(text))
        
        # Fallback to NLTK if LLaMA not available
        return self._extract_keywords_nltk_fallback(text)
    
    def _extract_keywords_nltk_fallback(self, text: str) -> List[str]:
        """Fallback NLTK-based keyword extraction"""
        if not NLTK_AVAILABLE:
            return []
        
        try:
            # Tokenize and get parts of speech
            words = word_tokenize(text.lower())
            pos_tags = nltk.pos_tag(words)
            
            # Extract nouns, verbs, and adjectives
            keywords = []
            for word, pos in pos_tags:
                if (pos.startswith('N') or pos.startswith('V') or pos.startswith('J')) and \
                   word not in self.stop_words and len(word) > 2:
                    keywords.append(word)
            
            # Get most frequent keywords
            from collections import Counter
            word_freq = Counter(keywords)
            return [word for word, count in word_freq.most_common(10)]
            
        except Exception as e:
            print(f"⚠️  NLTK keyword extraction failed: {e}")
            return []
    
    async def _extract_keywords_llama(self, text: str) -> List[str]:
        """Extract keywords using LLaMA-powered semantic analysis"""
        try:
            keyword_prompt = f"""[INST] You are a professional text analyst specializing in semantic keyword extraction for horror and ghost stories. Please analyze the following text and extract the most important and meaningful keywords that capture the essence of the content.

Text to analyze: {text}

Please extract keywords that are:
1. Semantically important to the story
2. Relevant for search and categorization
3. Representative of the main themes and concepts
4. Useful for content discovery and recommendation

Avoid common stop words and focus on nouns, significant verbs, and descriptive adjectives that define the story's character.

Respond in JSON format with a "keywords" array containing the most important keywords:
{{"keywords": ["keyword1", "keyword2", ...]}}

Limit to the 10 most important keywords. [/INST]"""
            
            # Call Ollama API
            response = requests.post(
                f"{self.model_config.ollama_base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": keyword_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.8,
                        "num_predict": 300
                    }
                },
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"❌ Ollama API error: {response.status_code}")
                return self._extract_keywords_nltk_fallback(text)
            
            result = response.json()
            response_text = result.get('response', '').strip()
            
            # Parse JSON response
            try:
                keyword_data = json.loads(response_text)
                keywords = keyword_data.get('keywords', [])
                
                # Validate and clean the results
                valid_keywords = []
                for keyword in keywords:
                    if (isinstance(keyword, str) and 
                        len(keyword.strip()) > 2 and 
                        len(keyword) < 25 and
                        keyword.lower() not in self.stop_words):
                        valid_keywords.append(keyword.strip().lower())
                
                return valid_keywords[:10]  # Limit to top 10
                
            except json.JSONDecodeError:
                print("⚠️  LLaMA keyword response not valid JSON, using NLTK fallback")
                return self._extract_keywords_nltk_fallback(text)
                
        except Exception as e:
            print(f"❌ LLaMA keyword extraction failed: {e}")
            return self._extract_keywords_nltk_fallback(text)
    
    async def chunk_story_with_gpt4o(self, story_text: str, title: str = "") -> List[EnglishChunk]:
        """
        Use GPT-4o-mini to intelligently chunk English ghost stories
        Preserves narrative structure and character development
        """
        if not self.is_initialized:
            raise RuntimeError("English processor not initialized - call initialize() first")
        
        start_time = datetime.now()
        chunks = []
        
        try:
            # Normalize the text first
            normalized_text = self.normalize_english_text(story_text)
            
            # Create chunking prompt for GPT-4o-mini
            chunking_prompt = f"""Intelligently segment the following English horror story to preserve narrative flow:

Title: {title}
Content: {normalized_text}

Requirements: ~{self.chunking_config.target_chunk_size // 4} words per chunk, natural breaks, preserve atmosphere, label chunk types"""
            
            # Rate limit OpenAI calls
            # await self._rate_limit_openai_call()
            
            # Call OpenAI API with structured parsing
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.parse,
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a professional text analyst, please return chunking information in JSON format"},
                    {"role": "user", "content": chunking_prompt}
                ],
                max_tokens=1500,  # Aligned with original English processor settings
                temperature=0.01,
                response_format=GPTChunkResponse
            )
            
            if not response or not response.choices:
                print("❌ GPT-4o-mini API error: no response")
                gpt_chunks = self._fallback_chunking(normalized_text)
            else:
                # Extract parsed data
                chunk_data = response.choices[0].message.parsed
                if chunk_data and chunk_data.chunks:
                    # Convert Pydantic models to dict format
                    gpt_chunks = []
                    for chunk in chunk_data.chunks:
                        gpt_chunks.append({
                            'text': chunk.text,
                            'type': chunk.type,
                            'order': chunk.order,
                            'keywords': chunk.keywords
                        })
                else:
                    print("⚠️  GPT-4o-mini response empty, falling back to rule-based chunking")
                    gpt_chunks = []
            
            # If GPT-4o-mini chunking fails, use fallback method
            if not gpt_chunks:
                gpt_chunks = self._fallback_chunking(normalized_text)
            
            # Process each chunk
            for i, chunk_info in enumerate(gpt_chunks):
                chunk_text = chunk_info.get('text', '').strip()
                if not chunk_text:
                    continue
                
                # Budget optimization: Use only essential metadata
                keywords = chunk_info.get('keywords', [])
                # Skip additional keyword extraction to save on API costs
                # if not keywords:  # Fallback keyword extraction
                #     keywords = self.extract_keywords_nltk(chunk_text)
                
                # Calculate metrics
                word_count = len(chunk_text.split())
                sentence_count = len(sent_tokenize(chunk_text)) if NLTK_AVAILABLE else chunk_text.count('.') + chunk_text.count('!') + chunk_text.count('?')
                dialogue_ratio = self.calculate_dialogue_ratio(chunk_text)
                
                chunk = EnglishChunk(
                    chunk_id=f"en_chunk_{i+1}",
                    original_text=chunk_text,
                    normalized_text=chunk_text,  # Already normalized
                    chunk_order=i + 1,
                    chunk_type=chunk_info.get('type', 'body').lower(),
                    character_count=len(chunk_text),  # Added for consistency
                    word_count=word_count,
                    sentence_count=sentence_count,
                    semantic_keywords=keywords[:10],  # Limit to top 10
                    dialogue_ratio=dialogue_ratio,
                    processing_metadata={
                        'model_used': 'gpt-4o-mini',
                        'processing_time': (datetime.now() - start_time).total_seconds(),
                        'normalization_applied': True,
                        'keyword_extraction_method': 'gpt4o' if self.is_initialized else ('nltk' if NLTK_AVAILABLE else 'regex')
                    }
                )
                
                chunks.append(chunk)
            
            # Processing completed successfully
            
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            print(f"✅ English story chunked: {len(chunks)} chunks ({processing_time_ms}ms)")
            
            return chunks
            
        except Exception as e:
            print(f"❌ English chunking failed: {e}")
            # Return fallback chunking on error
            return self._emergency_fallback_chunking(story_text)
    
    def _fallback_chunking(self, text: str) -> List[Dict]:
        """Fallback chunking method when LLaMA fails"""
        chunks = []
        target_words = self.chunking_config.target_chunk_size // 4  # Convert chars to words estimate
        
        # Split by sentences
        sentences = sent_tokenize(text) if NLTK_AVAILABLE else re.split(r'[.!?]+', text)
        
        current_chunk = ""
        current_word_count = 0
        chunk_count = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_words = len(sentence.split())
            
            if current_word_count + sentence_words > target_words and current_chunk:
                # Save current chunk
                chunks.append({
                    'text': current_chunk.strip(),
                    'type': 'body',
                    'order': chunk_count + 1,
                    'keywords': []
                })
                chunk_count += 1
                current_chunk = sentence + ". "
                current_word_count = sentence_words
            else:
                current_chunk += sentence + ". "
                current_word_count += sentence_words
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                'text': current_chunk.strip(),
                'type': 'ending' if chunk_count > 0 else 'body',
                'order': chunk_count + 1,
                'keywords': []
            })
        
        return chunks
    
    def _emergency_fallback_chunking(self, text: str) -> List[EnglishChunk]:
        """Emergency fallback when all else fails"""
        normalized_text = self.normalize_english_text(text)
        target_words = self.chunking_config.target_chunk_size // 4  # Convert chars to words
        
        words = normalized_text.split()
        chunks = []
        chunk_id = 1
        
        for i in range(0, len(words), target_words):
            chunk_words = words[i:i+target_words]
            chunk_text = ' '.join(chunk_words)
            
            if not chunk_text.strip():
                continue
            
            chunk = EnglishChunk(
                chunk_id=f"en_emergency_{chunk_id}",
                original_text=chunk_text,
                normalized_text=chunk_text,  # Updated field name
                chunk_order=chunk_id,
                chunk_type='body',
                character_count=len(chunk_text),  # Added for consistency
                word_count=len(chunk_words),
                sentence_count=chunk_text.count('.') + chunk_text.count('!') + chunk_text.count('?'),
                semantic_keywords=[],
                dialogue_ratio=0.0,
                processing_metadata={
                    'model_used': 'emergency_fallback',
                    'processing_time': 0,
                    'normalization_applied': True
                }
            )
            
            chunks.append(chunk)
            chunk_id += 1
        
        return chunks
    
    
    async def process_story(self, story_text: str, title: str = "", metadata: Dict = None) -> ProcessingResult:
        """
        Complete processing pipeline for English ghost stories
        
        Args:
            story_text: Raw English story text
            title: Story title (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            ProcessingResult with chunks and metadata
        """
        start_time = datetime.now()
        
        try:
            # Chunk the story using GPT-4o-mini
            chunks = await self.chunk_story_with_gpt4o(story_text, title)
            
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Update statistics
            self.processing_stats['total_processed'] += 1
            self.processing_stats['total_chunks'] += len(chunks)
            self.processing_stats['avg_processing_time'] = (
                (self.processing_stats['avg_processing_time'] * (self.processing_stats['total_processed'] - 1) + 
                 processing_time_ms) / self.processing_stats['total_processed']
            )
            
            # Processing completed
            
            result = ProcessingResult(
                success=True,
                chunks=chunks,
                processing_time_ms=processing_time_ms,
                metadata={
                    'language': 'en',
                    'total_words': len(story_text.split()),
                    'chunks_generated': len(chunks),
                    'model_used': 'gpt-4o-mini',
                    'normalization_applied': True,
                    'avg_dialogue_ratio': sum(chunk.dialogue_ratio for chunk in chunks) / len(chunks) if chunks else 0
                }
            )
            
            return result
            
        except Exception as e:
            error_msg = f"English processing failed: {str(e)}"
            print(f"❌ {error_msg}")
            
            self.processing_stats['errors'] += 1
            
            return ProcessingResult(
                success=False,
                chunks=[],
                processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error_message=error_msg
            )
    
    def get_processing_stats(self) -> Dict:
        """Get comprehensive processing statistics"""
        return {
            'processor_type': 'english_gpt4o_openai',
            'model_name': 'gpt-4o-mini',
            'openai_api': 'openai',
            'is_initialized': self.is_initialized,
            'processing_stats': self.processing_stats,
            'nltk_available': NLTK_AVAILABLE
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        # No model cleanup needed for OpenAI API
        print("🧹 English processor resources cleaned up")


# CLI interface for testing
async def main():
    """Test CLI for English processor"""
    import argparse
    
    parser = argparse.ArgumentParser(description="English Text Processor (LLaMA)")
    parser.add_argument('--text', type=str, help='English text to process')
    parser.add_argument('--file', type=str, help='File containing English text')
    parser.add_argument('--title', type=str, default='', help='Story title')
    parser.add_argument('--stats', action='store_true', help='Show processing statistics')
    
    args = parser.parse_args()
    
    processor = EnglishProcessor()
    
    try:
        if not await processor.initialize():
            print("❌ Failed to initialize English processor")
            return
        
        if args.stats:
            stats = processor.get_processing_stats()
            print(f"📊 Processing Statistics: {json.dumps(stats, indent=2)}")
        
        text = ""
        if args.text:
            text = args.text
        elif args.file:
            with open(args.file, 'r', encoding='utf-8') as f:
                text = f.read()
        
        if text:
            result = await processor.process_story(text, args.title)
            
            if result.success:
                print(f"\n✅ Processing successful:")
                print(f"   Chunks generated: {len(result.chunks)}")
                print(f"   Processing time: {result.processing_time_ms}ms")
                
                for i, chunk in enumerate(result.chunks[:3]):  # Show first 3 chunks
                    print(f"\n📝 Chunk {i+1} ({chunk.chunk_type}):")
                    print(f"   Text: {chunk.normalized_text[:100]}...")
                    print(f"   Keywords: {chunk.semantic_keywords}")
                    print(f"   Dialogue ratio: {chunk.dialogue_ratio:.2%}")
            else:
                print(f"❌ Processing failed: {result.error_message}")
        
    finally:
        await processor.cleanup()


if __name__ == "__main__":
    asyncio.run(main())