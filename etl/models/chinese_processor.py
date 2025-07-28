"""
Chinese Text Processor - DeepSeek Integration
Handles Traditional Chinese ghost story processing with DeepSeek models
"""

import asyncio
import unicodedata
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
from etl.config.config import CONFIG

# Pydantic models for structured parsing
class GPTChunk(BaseModel):
    """Enhanced chunk model with strict validation"""
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
    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        
        # Check for reasonable Chinese text content
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', v))
        if chinese_chars < len(v) * 0.3:  # At least 30% Chinese characters
            raise ValueError("Text must contain substantial Chinese content")
        
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
                    len(clean_keyword) <= 20 and
                    not clean_keyword.isspace()):
                    valid_keywords.append(clean_keyword)
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(valid_keywords))


class GPTChunkResponse(BaseModel):
    chunks: List[GPTChunk]

# Chinese text processing imports
try:
    import jieba
    import jieba.analyse
    import zhconv
    CHINESE_PROCESSING_AVAILABLE = True
except ImportError:
    CHINESE_PROCESSING_AVAILABLE = False

@dataclass
class ChineseChunk:
    """Chinese text chunk with semantic context"""
    chunk_id: str
    original_text: str
    normalized_text: str
    chunk_order: int
    character_count: int
    word_count: int
    semantic_keywords: List[str]
    processing_metadata: Dict[str, Any]
    chunk_type: Literal[
        "opening",
        "development",
        "body",
        "climax",
        "ending",
        "other"
    ] = "body"


@dataclass
class ProcessingResult:
    """Result of Chinese text processing"""
    success: bool
    chunks: List[ChineseChunk]
    processing_time_ms: int
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None


class ChineseProcessor:
    """
    Chinese text processor for Traditional Chinese ghost stories
    Handles character normalization, cultural context preservation, and semantic chunking
    """
    
    def _extract_json_from_response(self, response_text: str) -> Optional[Dict]:
        """Extract JSON from DeepSeek response, handling extra text"""
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
    
    async def _rate_limit_openai_call(self):
        """Ensure we don't exceed OpenAI rate limits"""
        current_time = time.time()
        elapsed = current_time - self.last_api_call
        
        if elapsed < self.min_call_interval:
            wait_time = self.min_call_interval - elapsed
            print(f"⏱️  Rate limiting: waiting {wait_time:.1f}s before OpenAI call")
            await asyncio.sleep(wait_time)
        
        self.last_api_call = time.time()
    
    def __init__(self, cache_dir: str = "./models"):
        """Initialize Chinese processor with Ollama DeepSeek model"""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Model configuration
        self.model_config = CONFIG["model"]
        self.chunking_config = CONFIG["chunking"]
        
        # OpenAI configuration
        self.openai_config = CONFIG["openai"]
        self.model_name = "gpt-4o-mini"  # Cost-effective and reliable
        self.is_initialized = False
        self.openai_client = None
        
        # Chinese processing setup
        self._setup_chinese_processors()
        
        # Processing statistics
        self.processing_stats = {
            'total_processed': 0,
            'total_chunks': 0,
            'avg_processing_time': 0.0,
            'errors': 0
        }
        
        # Rate limiting for OpenAI API (3 RPM limit)
        self.last_api_call = 0
        self.min_call_interval = 21  # 21 seconds between calls to stay under 3 RPM
    
    def _setup_chinese_processors(self):
        """Setup Chinese text processing tools"""
        if CHINESE_PROCESSING_AVAILABLE:
            # Initialize jieba for Chinese word segmentation
            # Only set custom dictionary if it exists
            dict_path = './dict.txt'
            if Path(dict_path).exists():
                jieba.set_dictionary(dict_path)
                print("✅ Chinese text processing tools initialized with custom dictionary")
            else:
                print("✅ Chinese text processing tools initialized with default dictionary")
        else:
            print("⚠️  Chinese processing libraries not available - install jieba and zhconv")
    
    async def initialize(self) -> bool:
        """Initialize OpenAI GPT-4o-mini for Chinese processing"""
        try:
            print("🚀 Initializing GPT-4o-mini for Chinese processing...")
            
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
                messages=[{"role": "user", "content": "測試"}],
                max_tokens=5,
                temperature=0.3
            )
            
            if not test_response:
                print("❌ GPT-4o-mini test failed")
                return False
            
            self.is_initialized = True
            print(f"✅ GPT-4o-mini initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ GPT-4o-mini initialization failed: {e}")
            # If Chinese libraries are available, we can still process with fallbacks
            if CHINESE_PROCESSING_AVAILABLE:
                print("⚡ Continuing with regex-based fallback methods")
                self.is_initialized = False  # Mark as not fully initialized
                return True  # But allow processing to continue
            return False
    
    async def normalize_chinese_text(self, text: str) -> str:
        """
        Normalize Traditional Chinese text with enhanced rule-based approach
        Handles character variants, encoding issues, and formatting
        """
        if not text:
            return ""
        
        # Use enhanced rule-based normalization (no LLM needed)
        return self._enhanced_normalize_chinese_text(text)
    
    def _enhanced_normalize_chinese_text(self, text: str) -> str:
        """Enhanced rule-based Chinese text normalization"""
        try:
            # Unicode normalization - CRITICAL for Chinese text
            text = unicodedata.normalize('NFKC', text)
            
            # Convert to Traditional Chinese if needed
            if CHINESE_PROCESSING_AVAILABLE:
                text = zhconv.convert(text, 'zh-tw')  # Convert to Traditional Chinese
            
            # Advanced formatting cleanup
            text = re.sub(r'\r\n|\r|\n', '\n', text)  # Normalize line endings
            text = re.sub(r'　+', '　', text)  # Normalize full-width spaces
            text = re.sub(r'[ \t]+', ' ', text)  # Normalize ASCII spaces and tabs
            text = re.sub(r'\n{3,}', '\n\n', text)  # Limit excessive newlines
            
            # Fix common typing errors
            text = re.sub(r'\.{3,}', '…', text)  # Multiple dots to ellipsis
            text = re.sub(r'(?<=[。！？])(?=[^」』）\s])', ' ', text)  # Add space after sentences
            
            # Remove or replace problematic characters
            text = text.replace('\u200b', '')  # Remove zero-width space
            text = text.replace('\ufeff', '')  # Remove BOM
            text = text.replace('\u00a0', ' ')  # Non-breaking space to regular space
            
            # Comprehensive punctuation normalization
            punct_map = {
                # Basic punctuation
                ',': '，', '.': '。', '?': '？', '!': '！',
                ':': '：', ';': '；', 
                # Brackets and quotes
                '(': '（', ')': '）', '[': '［', ']': '］',
                '{': '｛', '}': '｝', '<': '＜', '>': '＞',
                '"': '「', '"': '」', "'": '『', "'": '』',
                # Dashes and special chars
                '-': '－', '_': '＿', '/': '／', '\\': '＼',
                '*': '＊', '+': '＋', '=': '＝',
                # Numbers and symbols
                '$': '＄', '%': '％', '&': '＆', '@': '＠',
                '#': '＃', '^': '︿'
            }
            
            for en_punct, zh_punct in punct_map.items():
                text = text.replace(en_punct, zh_punct)
            
            # Normalize quotation marks consistently
            text = re.sub(r'「([^」]*?)」', r'「\1」', text)  # Ensure proper quote pairing
            text = re.sub(r'『([^』]*?)』', r'『\1』', text)  # Ensure proper quote pairing
            
            # Fix spacing around punctuation
            text = re.sub(r'\s+([，。！？：；）］｝」』])', r'\1', text)  # Remove space before closing punct
            text = re.sub(r'([（［｛「『])\s+', r'\1', text)  # Remove space after opening punct
            
            # Normalize repeated punctuation
            text = re.sub(r'([！？]){2,}', r'\1', text)  # Limit exclamation/question marks
            text = re.sub(r'([，；]){2,}', r'\1', text)  # Remove repeated commas/semicolons
            
            # Clean up excessive whitespace
            text = re.sub(r'　+', '　', text)  # Multiple full-width spaces to single
            text = re.sub(r' +', ' ', text)  # Multiple ASCII spaces to single
            text = re.sub(r'\n +', '\n', text)  # Remove leading spaces on new lines
            text = re.sub(r' +\n', '\n', text)  # Remove trailing spaces before newlines
            
            return text.strip()
            
        except Exception as e:
            print(f"❌ Enhanced text normalization failed: {e}")
            return text  # Return original if normalization fails
    
    async def _llm_enhance_normalization(self, text: str) -> Optional[str]:
        """Use Ollama DeepSeek to enhance text normalization"""
        try:
            normalization_prompt = f"""
            你是一個專業的繁體中文文本標準化專家。請對以下繁體中文文本進行進階標準化處理，改善文本品質但保持原意不變。 
            原文本：
            {text}

            請進行以下標準化處理：
            1. 統一標點符號使用（確保使用正確的中文標點）
            2. 修正明顯的錯字或異體字
            3. 統一詞彙用法（如：「裡面」vs「裏面」）
            4. 改善句子結構和流暢度
            5. 保持恐怖故事的語調和氛圍
            6. 移除多餘的空格或格式問題

            請直接回答標準化後的文本，不要添加額外說明。"""
            
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": normalization_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "top_p": 0.7,
                        "num_predict": 1024
                    }
                },
                timeout=300
            )
            
            if response.status_code != 200:
                print(f"❌ Ollama API error: {response.status_code}")
                return None
            
            result = response.json()
            normalized_text = result.get('response', '').strip()
            
            # Validate the normalized text
            if (len(normalized_text) > len(text) * 0.5 and  # Not too short
                len(normalized_text) < len(text) * 2 and      # Not too long
                normalized_text and                            # Not empty
                '```' not in normalized_text):                # No code blocks
                return normalized_text
            else:
                return None  # Use basic normalization
                
        except Exception as e:
            print(f"❌ LLM text normalization failed: {e}")
            return None
    
    
    def segment_chinese_text(self, text: str) -> List[str]:
        """Segment Chinese text into words using jieba"""
        if CHINESE_PROCESSING_AVAILABLE:
            return list(jieba.cut(text, cut_all=False))
        else:
            # Fallback: character-based segmentation
            return list(text)
    
    def extract_keywords_tfidf(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords using TF-IDF with jieba analysis"""
        if not CHINESE_PROCESSING_AVAILABLE:
            # Fallback to simple frequency analysis
            return self._extract_keywords_fallback(text, max_keywords)
        
        try:
            # Use jieba TF-IDF keyword extraction
            keywords = jieba.analyse.extract_tags(
                text, 
                topK=max_keywords * 2,  # Get more to filter for horror relevance
                withWeight=False
            )
            
            # Filter for horror/ghost story relevance
            horror_keywords = []
            horror_terms = {
                '鬼', '靈', '死', '黑', '夜', '恐怖', '害怕', '陰', '血', '哭',
                '魂', '墓', '廟', '寺', '怪', '妖', '驚', '嚇', '陰森', '詭異',
                '恐懼', '煞', '祟', '邪', '凶', '厲', '怨', '冷', '暗', '影'
            }
            
            for keyword in keywords:
                # Check if keyword contains horror-relevant terms or is contextually relevant
                if (len(keyword) > 1 and 
                    (any(term in keyword for term in horror_terms) or 
                     self._is_contextually_relevant(keyword, text))):
                    horror_keywords.append(keyword)
                    
                if len(horror_keywords) >= max_keywords:
                    break
            
            # If not enough horror keywords, add high-scoring general keywords
            if len(horror_keywords) < max_keywords // 2:
                for keyword in keywords:
                    if keyword not in horror_keywords and len(keyword) > 1:
                        horror_keywords.append(keyword)
                        if len(horror_keywords) >= max_keywords:
                            break
            
            return horror_keywords[:max_keywords]
            
        except Exception as e:
            print(f"❌ TF-IDF keyword extraction failed: {e}")
            return self._extract_keywords_fallback(text, max_keywords)
    
    def _is_contextually_relevant(self, keyword: str, text: str) -> bool:
        """Check if a keyword is contextually relevant to horror stories"""
        # Count frequency of keyword in text
        keyword_count = text.count(keyword)
        if keyword_count < 2:
            return False
        
        # Check surrounding context for horror elements
        horror_context_terms = {
            '突然', '忽然', '瞬間', '驚', '叫', '血', '冰冷', '陰暗',
            '恐怖', '害怕', '恐懼', '詭異', '陰森', '毛骨悚然'
        }
        
        # Find keyword occurrences and check nearby context
        import re
        keyword_positions = [m.start() for m in re.finditer(re.escape(keyword), text)]
        
        for pos in keyword_positions:
            # Check 50 characters before and after
            context_start = max(0, pos - 50)
            context_end = min(len(text), pos + len(keyword) + 50)
            context = text[context_start:context_end]
            
            if any(term in context for term in horror_context_terms):
                return True
        
        return False
    
    def _extract_keywords_fallback(self, text: str, max_keywords: int) -> List[str]:
        """Fallback keyword extraction using simple frequency analysis"""
        # Split text into potential keywords (2+ characters)
        words = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        
        # Count frequencies
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and filter
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        # Filter for relevance
        keywords = []
        for word, freq in sorted_words:
            if freq >= 2 and len(word) <= 6:  # Reasonable word length
                keywords.append(word)
                if len(keywords) >= max_keywords:
                    break
        
        return keywords
    
    async def chunk_story_with_gpt4o(self, story_text: str, title: str = "") -> List[ChineseChunk]:
        """
        Use GPT-4o-mini to intelligently chunk Chinese ghost stories
        Preserves narrative flow and cultural context
        """
        if not self.is_initialized:
            raise RuntimeError("Chinese processor not initialized - call initialize() first")
        
        start_time = datetime.now()
        chunks = []
        
        try:
            # Normalize the text first
            normalized_text = await self.normalize_chinese_text(story_text)
            
            # Create chunking prompt for GPT-4o-mini
            chunking_prompt = f"""
            將以下中文恐怖故事智能分段：
            標題：{title}
            內容：{normalized_text}
            要求：每段{self.chunking_config.target_chunk_size}字、自然分段、保持氛圍、標註類型
            """
                        
            # Rate limit OpenAI calls
            # await self._rate_limit_openai_call()
            
            # Call OpenAI API with structured parsing
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.parse,
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "你是一個專業的文本分析師，請按照 JSON 格式回傳分段資訊"},
                    {"role": "user", "content": chunking_prompt}
                ],
                max_tokens=10000,
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
                
                # Extract metadata using enhanced methods
                # tfidf_keywords = self.extract_keywords_tfidf(chunk_text, 10)
                # Use only LLM keywords from chunking response
                llm_keywords = chunk_info.get('keywords', [])
                
                # Use only LLM keywords (no additional keyword extraction)
                combined_keywords = llm_keywords
                
                # Prepare keywords
                
                # Word segmentation
                words = self.segment_chinese_text(chunk_text)
                
                chunk = ChineseChunk(
                    chunk_id=f"zh_chunk_{i+1}",
                    original_text=chunk_text,
                    normalized_text=chunk_text,  # Already normalized
                    chunk_order=i + 1,
                    chunk_type=chunk_info.get('type', 'body').lower(),
                    character_count=len(chunk_text),
                    word_count=len(words),
                    semantic_keywords=combined_keywords[:10],  # Limit to top 10

                    processing_metadata={
                        'model_used': 'gpt-4o-mini',
                        'processing_time': (datetime.now() - start_time).total_seconds(),
                        'normalization_applied': True,
                        'segmentation_method': 'jieba' if CHINESE_PROCESSING_AVAILABLE else 'character',
                    }
                )
                
                chunks.append(chunk)
            
            # Processing completed successfully
            
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            print(f"✅ Chinese story chunked: {len(chunks)} chunks ({processing_time_ms}ms)")
            
            return chunks
            
        except Exception as e:
            print(f"❌ Chinese chunking failed: {e}")
            # Return fallback chunking on error
            return await self._emergency_fallback_chunking(story_text)
    
    def _fallback_chunking(self, text: str) -> List[Dict]:
        """Fallback chunking method when DeepSeek fails"""
        chunks = []
        target_size = self.chunking_config.target_chunk_size
        sentences = re.split(r'[。！？]', text)
        
        current_chunk = ""
        chunk_count = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_chunk) + len(sentence) > target_size and current_chunk:
                # Save current chunk
                chunks.append({
                    'text': current_chunk.strip(),
                    'type': 'body',
                    'order': chunk_count + 1,
                    'keywords': []
                })
                chunk_count += 1
                current_chunk = sentence
            else:
                current_chunk += sentence + "。"
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append({
                'text': current_chunk.strip(),
                'type': 'ending' if chunk_count > 0 else 'body',
                'order': chunk_count + 1,
                'keywords': []
            })
        
        return chunks
    
    async def _emergency_fallback_chunking(self, text: str) -> List[ChineseChunk]:
        """Emergency fallback when all else fails"""
        normalized_text = await self.normalize_chinese_text(text)
        target_size = self.chunking_config.target_chunk_size
        
        chunks = []
        chunk_id = 1
        
        for i in range(0, len(normalized_text), target_size):
            chunk_text = normalized_text[i:i+target_size]
            if not chunk_text.strip():
                continue
            
            

            chunk = ChineseChunk(
                chunk_id=f"zh_emergency_{chunk_id}",
                original_text=chunk_text,
                normalized_text=chunk_text,
                chunk_order=chunk_id,
                chunk_type='body',
                character_count=len(chunk_text),
                word_count=len(chunk_text),  # Approximation
                semantic_keywords=self.extract_keywords_tfidf(chunk_text), # Utilizing tf-idf for keywords extraction
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
        Complete processing pipeline for Chinese ghost stories
        
        Args:
            story_text: Raw Chinese story text
            title: Story title (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            ProcessingResult with chunks and metadata
        """
        start_time = datetime.now()
        
        try:
            # Chunk the story using gpt4o
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
                    'language': 'zh',
                    'total_characters': len(story_text),
                    'chunks_generated': len(chunks),
                    'model_used': 'gpt-4o-mini',
                    'normalization_applied': True
                }
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Chinese processing failed: {str(e)}"
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
            'processor_type': 'chinese_gpt4o_openai',
            'model_name': 'gpt-4o-mini',
            'openai_api': 'openai',
            'is_initialized': self.is_initialized,
            'processing_stats': self.processing_stats,
            'chinese_processing_available': CHINESE_PROCESSING_AVAILABLE
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        # No model cleanup needed for Ollama API
        print("🧹 Chinese processor resources cleaned up")


# CLI interface for testing
async def main():
    """Test CLI for Chinese processor"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Chinese Text Processor (DeepSeek)")
    parser.add_argument('--text', type=str, help='Chinese text to process')
    parser.add_argument('--file', type=str, help='File containing Chinese text')
    parser.add_argument('--title', type=str, default='', help='Story title')
    parser.add_argument('--stats', action='store_true', help='Show processing statistics')
    
    args = parser.parse_args()
    
    processor = ChineseProcessor()
    
    try:
        if not await processor.initialize():
            print("❌ Failed to initialize Chinese processor")
            return
        
        if args.stats:
            stats = processor.get_processing_stats()
            print(f"📊 Processing Statistics: {json.dumps(stats, indent=2, ensure_ascii=False)}")
        
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
                    print(f"   Cultural entities: {chunk.cultural_entities}")
                    print(f"   Emotions: {chunk.emotion_indicators}")
            else:
                print(f"❌ Processing failed: {result.error_message}")
        
    finally:
        await processor.cleanup()


if __name__ == "__main__":
    asyncio.run(main())