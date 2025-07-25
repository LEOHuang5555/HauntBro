"""
Chinese Text Processor - DeepSeek Integration
Handles Traditional Chinese ghost story processing with DeepSeek models
"""

import asyncio
import torch
import unicodedata
import re
import json
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import openai
from pathlib import Path
import sys

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from etl.processing.config import CONFIG

# Transformers imports for DeepSeek
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# Chinese text processing imports
try:
    import jieba
    import zhconv
    CHINESE_PROCESSING_AVAILABLE = True
except ImportError:
    CHINESE_PROCESSING_AVAILABLE = False


@dataclass
class ChineseChunk:
    """Chinese text chunk with cultural context"""
    chunk_id: str
    original_text: str
    normalized_text: str
    chunk_order: int
    chunk_type: str  # 'opening', 'body', 'climax', 'ending'
    character_count: int
    word_count: int
    semantic_keywords: List[str]
    cultural_entities: List[str]  # Places, folklore, cultural references
    emotion_indicators: List[str]  # Fear, suspense indicators
    processing_metadata: Dict[str, Any]


@dataclass
class ProcessingResult:
    """Result of Chinese text processing"""
    success: bool
    chunks: List[ChineseChunk]
    processing_time_ms: int
    model_cost: float
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None


class ChineseProcessor:
    """
    DeepSeek-powered Chinese text processor for Traditional Chinese ghost stories
    Handles character normalization, cultural context preservation, and semantic chunking
    """
    
    def __init__(self, cache_dir: str = "./models"):
        """Initialize Chinese processor with DeepSeek model"""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Model configuration
        self.model_config = CONFIG["model"]
        self.chunking_config = CONFIG["chunking"]
        
        # DeepSeek model setup
        self.tokenizer = None
        self.model = None
        self.is_initialized = False
        
        # Chinese processing setup
        self._setup_chinese_processors()
        
        # Cost tracking
        self.total_cost = 0.0
        self.processing_stats = {
            'total_processed': 0,
            'total_chunks': 0,
            'avg_processing_time': 0.0,
            'errors': 0
        }
    
    def _setup_chinese_processors(self):
        """Setup Chinese text processing tools"""
        if CHINESE_PROCESSING_AVAILABLE:
            # Initialize jieba for Chinese word segmentation
            jieba.set_dictionary('./dict.txt')  # Custom dictionary if available
            print("✅ Chinese text processing tools initialized")
        else:
            print("⚠️  Chinese processing libraries not available - install jieba and zhconv")
    
    async def initialize(self) -> bool:
        """Initialize DeepSeek model for Chinese processing"""
        if not TRANSFORMERS_AVAILABLE:
            print("❌ Transformers library not available")
            return False
        
        try:
            print("🚀 Initializing DeepSeek model for Chinese processing...")
            
            # DeepSeek model configuration
            model_name = "deepseek-ai/deepseek-coder-6.7b-instruct"
            
            # Configure quantization for memory efficiency
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16
            )
            
            print("Loading DeepSeek tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=self.cache_dir,
                trust_remote_code=True
            )
            
            # Add padding token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            print("Loading DeepSeek model...")
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=bnb_config,
                device_map="auto",
                cache_dir=self.cache_dir,
                trust_remote_code=True,
                torch_dtype=torch.float16
            )
            
            self.is_initialized = True
            print(f"✅ DeepSeek model loaded on {self.device}")
            return True
            
        except Exception as e:
            print(f"❌ DeepSeek initialization failed: {e}")
            return False
    
    def normalize_chinese_text(self, text: str) -> str:
        """
        Normalize Traditional Chinese text for consistent processing
        Handles character variants, encoding issues, and formatting
        """
        if not text:
            return ""
        
        try:
            # Unicode normalization - CRITICAL for Chinese text
            text = unicodedata.normalize('NFKC', text)
            
            # Convert to Traditional Chinese if needed
            if CHINESE_PROCESSING_AVAILABLE:
                text = zhconv.convert(text, 'zh-tw')  # Convert to Traditional Chinese
            
            # Clean up common formatting issues
            text = re.sub(r'\r\n|\r|\n', '\n', text)  # Normalize line endings
            text = re.sub(r'　+', '　', text)  # Normalize full-width spaces
            text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
            text = re.sub(r'\.{3,}', '…', text)  # Replace multiple dots with ellipsis
            
            # Remove or replace problematic characters
            text = text.replace('\u200b', '')  # Remove zero-width space
            text = text.replace('\ufeff', '')  # Remove BOM
            
            # Normalize punctuation
            punct_map = {
                ',': '，', '.': '。', '?': '？', '!': '！',
                ':': '：', ';': '；', '(': '（', ')': '）',
                '[': '［', ']': '］', '"': '「', '"': '」'
            }
            
            for en_punct, zh_punct in punct_map.items():
                text = text.replace(en_punct, zh_punct)
            
            return text.strip()
            
        except Exception as e:
            print(f"❌ Text normalization failed: {e}")
            return text  # Return original if normalization fails
    
    def extract_cultural_entities(self, text: str) -> List[str]:
        """Extract Chinese cultural entities and references"""
        entities = []
        
        # Common ghost story cultural elements
        cultural_patterns = [
            # Places
            r'(廟|寺|墓地|墳墓|學校|醫院|宿舍|老屋|古厝)',
            # Supernatural entities
            r'(鬼|魂|靈|妖|怪|陰魂|孤魂|野鬼)',
            # Time references
            r'(子時|半夜|深夜|午夜|鬼月|農曆|七月)',
            # Religious/spiritual
            r'(拜拜|燒香|符咒|法師|道士|和尚|佛珠|護身符)',
            # Traditional items
            r'(紅包|香|紙錢|供品|祭品|神主牌|香爐)'
        ]
        
        for pattern in cultural_patterns:
            matches = re.findall(pattern, text)
            entities.extend(matches)
        
        return list(set(entities))  # Remove duplicates
    
    def extract_emotion_indicators(self, text: str) -> List[str]:
        """Extract emotional indicators specific to horror/ghost stories"""
        emotions = []
        
        # Fear and suspense indicators in Chinese
        emotion_patterns = [
            # Fear expressions
            r'(害怕|恐懼|驚嚇|膽戰心驚|毛骨悚然)',
            # Physical reactions
            r'(起雞皮疙瘩|汗毛直豎|心臟狂跳|手腳發軟)',
            # Atmosphere
            r'(陰森|詭異|毛骨悚然|令人不安|詭譎)',
            # Sound effects
            r'(尖叫|慘叫|哭聲|腳步聲|敲門聲)',
            # Visual descriptions
            r'(慘白|血紅|漆黑|陰暗|模糊)'
        ]
        
        for pattern in emotion_patterns:
            matches = re.findall(pattern, text)
            emotions.extend(matches)
        
        return list(set(emotions))
    
    def segment_chinese_text(self, text: str) -> List[str]:
        """Segment Chinese text into words using jieba"""
        if CHINESE_PROCESSING_AVAILABLE:
            return list(jieba.cut(text, cut_all=False))
        else:
            # Fallback: character-based segmentation
            return list(text)
    
    async def chunk_story_with_deepseek(self, story_text: str, title: str = "") -> List[ChineseChunk]:
        """
        Use DeepSeek to intelligently chunk Chinese ghost stories
        Preserves narrative flow and cultural context
        """
        if not self.is_initialized:
            raise RuntimeError("Chinese processor not initialized - call initialize() first")
        
        start_time = datetime.now()
        chunks = []
        
        try:
            # Normalize the text first
            normalized_text = self.normalize_chinese_text(story_text)
            
            # Create chunking prompt for DeepSeek
            chunking_prompt = f"""
你是一個專業的中文文本分析師，專門處理恐怖小說和鬼故事。
請將以下故事智能分段，保持故事的敘事流程和文化語境。

故事標題：{title}
故事內容：{normalized_text}

請按照以下要求分段：
1. 每段約{self.chunking_config.target_chunk_size}個字符
2. 在自然的段落或情節轉折處分段
3. 保持恐怖氛圍的完整性
4. 為每段標註類型：開頭/發展/高潮/結尾

請以JSON格式回答，包含chunks陣列，每個chunk包含：
- text: 分段文本
- type: 段落類型
- order: 順序號
- keywords: 關鍵詞列表
"""
            
            # Tokenize the prompt
            inputs = self.tokenizer.encode(
                chunking_prompt, 
                return_tensors="pt", 
                max_length=4096,
                truncation=True
            ).to(self.device)
            
            # Generate response with DeepSeek
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_new_tokens=2048,
                    temperature=self.model_config.temperature,
                    top_p=self.model_config.top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            response_text = response[len(chunking_prompt):].strip()
            
            # Parse JSON response from DeepSeek
            try:
                chunk_data = json.loads(response_text)
                deepseek_chunks = chunk_data.get('chunks', [])
            except json.JSONDecodeError:
                print("⚠️  DeepSeek response not valid JSON, falling back to rule-based chunking")
                deepseek_chunks = []
            
            # If DeepSeek chunking fails, use fallback method
            if not deepseek_chunks:
                deepseek_chunks = self._fallback_chunking(normalized_text)
            
            # Process each chunk
            for i, chunk_info in enumerate(deepseek_chunks):
                chunk_text = chunk_info.get('text', '').strip()
                if not chunk_text:
                    continue
                
                # Extract metadata
                cultural_entities = self.extract_cultural_entities(chunk_text)
                emotion_indicators = self.extract_emotion_indicators(chunk_text)
                keywords = chunk_info.get('keywords', [])
                
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
                    semantic_keywords=keywords[:10],  # Limit to top 10
                    cultural_entities=cultural_entities[:5],  # Limit to top 5
                    emotion_indicators=emotion_indicators[:5],  # Limit to top 5
                    processing_metadata={
                        'model_used': 'deepseek-coder-6.7b-instruct',
                        'processing_time': (datetime.now() - start_time).total_seconds(),
                        'normalization_applied': True,
                        'segmentation_method': 'jieba' if CHINESE_PROCESSING_AVAILABLE else 'character'
                    }
                )
                
                chunks.append(chunk)
            
            # Calculate cost (estimate based on tokens)
            total_tokens = len(inputs[0]) + sum(len(self.tokenizer.encode(chunk.normalized_text)) for chunk in chunks)
            estimated_cost = self._calculate_processing_cost(total_tokens)
            self.total_cost += estimated_cost
            
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            print(f"✅ Chinese story chunked: {len(chunks)} chunks ({processing_time_ms}ms)")
            
            return chunks
            
        except Exception as e:
            print(f"❌ Chinese chunking failed: {e}")
            # Return fallback chunking on error
            return self._emergency_fallback_chunking(story_text)
    
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
    
    def _emergency_fallback_chunking(self, text: str) -> List[ChineseChunk]:
        """Emergency fallback when all else fails"""
        normalized_text = self.normalize_chinese_text(text)
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
                semantic_keywords=[],
                cultural_entities=[],
                emotion_indicators=[],
                processing_metadata={
                    'model_used': 'emergency_fallback',
                    'processing_time': 0,
                    'normalization_applied': True
                }
            )
            
            chunks.append(chunk)
            chunk_id += 1
        
        return chunks
    
    def _calculate_processing_cost(self, total_tokens: int) -> float:
        """Calculate estimated processing cost for DeepSeek usage"""
        # Estimated cost per 1K tokens (adjust based on actual pricing)
        cost_per_1k_tokens = 0.002  # $0.002 per 1K tokens (estimate)
        return (total_tokens / 1000) * cost_per_1k_tokens
    
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
            # Chunk the story using DeepSeek
            chunks = await self.chunk_story_with_deepseek(story_text, title)
            
            processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Update statistics
            self.processing_stats['total_processed'] += 1
            self.processing_stats['total_chunks'] += len(chunks)
            self.processing_stats['avg_processing_time'] = (
                (self.processing_stats['avg_processing_time'] * (self.processing_stats['total_processed'] - 1) + 
                 processing_time_ms) / self.processing_stats['total_processed']
            )
            
            # Calculate total cost for this processing
            total_cost = sum(
                self._calculate_processing_cost(chunk.character_count) 
                for chunk in chunks
            )
            
            result = ProcessingResult(
                success=True,
                chunks=chunks,
                processing_time_ms=processing_time_ms,
                model_cost=total_cost,
                metadata={
                    'language': 'zh',
                    'total_characters': len(story_text),
                    'chunks_generated': len(chunks),
                    'model_used': 'deepseek-coder-6.7b-instruct',
                    'normalization_applied': True,
                    'cultural_entities_found': sum(len(chunk.cultural_entities) for chunk in chunks),
                    'emotion_indicators_found': sum(len(chunk.emotion_indicators) for chunk in chunks)
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
                model_cost=0.0,
                error_message=error_msg
            )
    
    def get_processing_stats(self) -> Dict:
        """Get comprehensive processing statistics"""
        return {
            'processor_type': 'chinese_deepseek',
            'model_name': 'deepseek-coder-6.7b-instruct',
            'device': self.device,
            'is_initialized': self.is_initialized,
            'total_cost': self.total_cost,
            'processing_stats': self.processing_stats,
            'chinese_processing_available': CHINESE_PROCESSING_AVAILABLE,
            'transformers_available': TRANSFORMERS_AVAILABLE
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.model:
            del self.model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
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
                print(f"   Estimated cost: ${result.model_cost:.4f}")
                
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