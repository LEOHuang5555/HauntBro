import re
import uuid
import json
import asyncio
import aiohttp
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from langdetect import detect, LangDetectError
import jieba  # Chinese text segmentation
import nltk
from nltk.tokenize import sent_tokenize
# Remove duplicate import
from config import CONFIG

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

@dataclass
class ChunkConfig:
    """Configuration for chunking parameters"""
    target_chunk_size: int = 512  # Target tokens per chunk
    max_chunk_size: int = 768     # Maximum tokens per chunk
    overlap_size: int = 64        # Overlap between chunks
    min_chunk_size: int = 100     # Minimum viable chunk size
    context_window: int = 128     # Additional context around chunk

@dataclass
class StoryChunk:
    """Represents a processed story chunk"""
    id: str
    story_id: str
    chunk_text: str
    chunk_context: str
    chunk_order: int
    chunk_type: str
    overlap_start: int
    overlap_end: int
    chunk_length: int
    chunk_word_count: int
    semantic_keywords: List[str]
    content_embedding: Optional[List[float]] = None
    search_embedding: Optional[List[float]] = None
    language: str = "unknown"
    processing_metadata: Dict = None

class LanguageDetector:
    """Enhanced language detection for Chinese/English content"""
    
    @staticmethod
    def detect_language(text: str) -> str:
        """Detect primary language with confidence scoring"""
        try:
            # Character-based detection
            chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
            total_chars = len(text.replace(' ', '').replace('\n', ''))
            
            if total_chars == 0:
                return 'unknown'
            
            chinese_ratio = chinese_chars / total_chars
            
            # High confidence Chinese
            if chinese_ratio > 0.7:
                return 'zh'
            
            # High confidence English  
            if chinese_ratio < 0.1:
                english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
                if english_words > 10:
                    return 'en'
            
            # Mixed content - use library detection
            detected = detect(text)
            if detected in ['zh-cn', 'zh-tw', 'zh']:
                return 'zh'
            elif detected == 'en':
                return 'en'
            else:
                # Fallback to ratio-based decision
                return 'zh' if chinese_ratio > 0.3 else 'en'
                
        except LangDetectError:
            # Fallback to character analysis
            chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
            total_chars = len(text.replace(' ', ''))
            return 'zh' if chinese_chars / max(total_chars, 1) > 0.3 else 'en'

class ModelClient:
    """Client for interacting with local LLM models"""
    
    def __init__(self, ollama_base_url: str = None):
        # Use config instead of hardcoded URL
        self.ollama_base_url = ollama_base_url or CONFIG["model"].ollama_base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def chunk_with_llama(self, text: str, config: ChunkConfig) -> List[Dict]:
        """Use LLaMA3 to intelligently chunk English text"""
        prompt = f"""
Task: Split this English story into semantic chunks for better searchability.

Requirements:
- Each chunk should be {config.target_chunk_size}-{config.max_chunk_size} characters
- Maintain narrative coherence 
- Break at natural story boundaries (scene changes, dialogue breaks, time shifts)
- Ensure each chunk can stand alone for search purposes

Story text:
{text}

Return a JSON array where each chunk has:
- "text": the chunk content
- "type": "opening", "development", "climax", "resolution", or "body"
- "summary": brief description of what happens in this chunk

Response format: {{"chunks": [...]}}
"""
        
        payload = {
            "model": CONFIG["model"].english_model,  # Use config model
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": CONFIG["model"].temperature,
                "top_p": CONFIG["model"].top_p,
                "max_tokens": 2048
            }
        }
        
        try:
            async with self.session.post(
                f"{self.ollama_base_url}/api/generate", 
                json=payload
            ) as response:
                result = await response.json()
                
                # Parse LLM response
                llm_output = result.get('response', '')
                return self._parse_llm_chunks(llm_output, 'en')
                
        except Exception as e:
            print(f"LLaMA chunking failed: {e}")
            return self._fallback_chunking(text, 'en', config)
    
    async def chunk_with_deepseek(self, text: str, config: ChunkConfig) -> List[Dict]:
        """Use Deepseek to intelligently chunk Mandarin text"""
        prompt = f"""
任務：將這個中文故事分割成語義塊，以便更好地搜索。

要求：
- 每個塊應該是{config.target_chunk_size}-{config.max_chunk_size}個字符
- 保持敘事連貫性
- 在自然的故事邊界處分割（場景變化、對話間斷、時間轉換）
- 確保每個塊都可以獨立進行搜索

故事文本：
{text}

返回JSON數組，每個塊包含：
- "text": 塊內容
- "type": "開頭", "發展", "高潮", "結尾", 或 "主體"
- "summary": 這個塊中發生的事情的簡要描述

響應格式: {{"chunks": [...]}}
"""
        
        payload = {
            "model": CONFIG["model"].chinese_model,  # Use config model
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": CONFIG["model"].temperature,
                "top_p": CONFIG["model"].top_p,
                "max_tokens": 2048
            }
        }
        
        try:
            async with self.session.post(
                f"{self.ollama_base_url}/api/generate", 
                json=payload
            ) as response:
                result = await response.json()
                
                # Parse LLM response
                llm_output = result.get('response', '')
                return self._parse_llm_chunks(llm_output, 'zh')
                
        except Exception as e:
            print(f"Deepseek chunking failed: {e}")
            return self._fallback_chunking(text, 'zh', config)
    
    def _parse_llm_chunks(self, llm_output: str, language: str) -> List[Dict]:
        """Parse LLM response into structured chunks"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', llm_output, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                if 'chunks' in parsed:
                    return parsed['chunks']
            
            # Fallback: parse structured text
            chunks = []
            current_chunk = {"text": "", "type": "body", "summary": ""}
            
            lines = llm_output.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('"text":') or line.startswith('text:'):
                    current_chunk["text"] = line.split(':', 1)[1].strip().strip('"')
                elif line.startswith('"type":') or line.startswith('type:'):
                    current_chunk["type"] = line.split(':', 1)[1].strip().strip('"')
                elif line.startswith('"summary":') or line.startswith('summary:'):
                    current_chunk["summary"] = line.split(':', 1)[1].strip().strip('"')
                    if current_chunk["text"]:
                        chunks.append(current_chunk.copy())
                        current_chunk = {"text": "", "type": "body", "summary": ""}
            
            return chunks if chunks else []
            
        except Exception as e:
            print(f"Failed to parse LLM output: {e}")
            return []
    
    def _fallback_chunking(self, text: str, language: str, config: ChunkConfig) -> List[Dict]:
        """Fallback rule-based chunking when LLM fails"""
        chunks = []
        
        if language == 'zh':
            # Chinese sentence segmentation
            sentences = re.split(r'[。！？]', text)
        else:
            # English sentence segmentation
            sentences = sent_tokenize(text)
        
        current_chunk = []
        current_length = 0
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_length = len(sentence)
            
            if current_length + sentence_length > config.target_chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk) if language == 'en' else ''.join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "type": self._infer_chunk_type(i, len(sentences), chunk_text),
                    "summary": f"Chunk {len(chunks) + 1}"
                })
                
                # Start new chunk with overlap
                overlap_sentences = current_chunk[-1:] if current_chunk else []
                current_chunk = overlap_sentences + [sentence]
                current_length = sum(len(s) for s in current_chunk)
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk) if language == 'en' else ''.join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "type": "ending" if chunks else "body",
                "summary": f"Final chunk"
            })
        
        return chunks
    
    def _infer_chunk_type(self, sentence_idx: int, total_sentences: int, text: str) -> str:
        """Infer chunk type based on position and content"""
        position_ratio = sentence_idx / max(total_sentences, 1)
        
        if position_ratio < 0.2:
            return "opening"
        elif position_ratio > 0.8:
            return "ending"
        elif 0.4 <= position_ratio <= 0.7:
            # Check for climax indicators
            climax_words = ['suddenly', 'scream', 'blood', 'death', '突然', '尖叫', '血', '死']
            if any(word in text.lower() for word in climax_words):
                return "climax"
        
        return "development"

# Remove duplicate EmbeddingGenerator class - use from embedding.py
from embedding import EmbeddingGenerator

class KeywordExtractor:
    """Extract semantic keywords from chunks"""
    
    def __init__(self):
        # Initialize for both languages
        jieba.initialize()
    
    def extract_keywords(self, text: str, language: str, max_keywords: int = 10) -> List[str]:
        """Extract meaningful keywords from text"""
        keywords = []
        
        try:
            if language == 'zh':
                # Chinese keyword extraction
                words = jieba.analyse.extract_tags(text, topK=max_keywords, withWeight=False)
                keywords.extend(words)
                
                # Add named entity patterns
                entities = re.findall(r'[\u4e00-\u9fff]{2,4}(?:先生|女士|老师|医生)', text)
                keywords.extend(entities[:5])
                
            else:
                # English keyword extraction
                words = text.lower().split()
                # Simple frequency-based extraction (you can enhance this)
                word_freq = {}
                for word in words:
                    if len(word) > 3 and word.isalpha():
                        word_freq[word] = word_freq.get(word, 0) + 1
                
                # Get top keywords
                sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
                keywords.extend([word for word, freq in sorted_words[:max_keywords]])
        
        except Exception as e:
            print(f"Keyword extraction failed: {e}")
        
        return list(set(keywords))  # Remove duplicates

class StoryChunker:
    """Main chunking orchestrator"""
    
    def __init__(self, config: ChunkConfig = None):
        self.config = config or ChunkConfig()
        self.language_detector = LanguageDetector()
        self.embedding_generator = EmbeddingGenerator()
        self.keyword_extractor = KeywordExtractor()
    
    async def chunk_story(self, story_id: str, content: str, title: str = "") -> List[StoryChunk]:
        """Main method to chunk a story with LLM assistance"""
        
        # Detect language
        language = self.language_detector.detect_language(content)
        print(f"Detected language: {language}")
        
        # Get LLM-assisted chunks
        async with ModelClient() as client:
            if language == 'zh':
                llm_chunks = await client.chunk_with_deepseek(content, self.config)
            else:
                llm_chunks = await client.chunk_with_llama(content, self.config)
        
        # Process chunks into StoryChunk objects
        story_chunks = []
        
        for i, chunk_data in enumerate(llm_chunks):
            chunk_text = chunk_data.get('text', '')
            if len(chunk_text) < self.config.min_chunk_size:
                continue
            
            # Create extended context
            chunk_context = self._create_context(chunk_text, llm_chunks, i)
            
            # Generate embeddings
            content_embedding, search_embedding = self.embedding_generator.generate_embeddings(
                chunk_text, chunk_context
            )
            
            # Extract keywords
            keywords = self.keyword_extractor.extract_keywords(chunk_text, language)
            
            # Calculate word count
            if language == 'zh':
                word_count = len(chunk_text)  # Character count for Chinese
            else:
                word_count = len(chunk_text.split())
            
            # Create chunk object
            chunk = StoryChunk(
                id=str(uuid.uuid4()),
                story_id=story_id,
                chunk_text=chunk_text,
                chunk_context=chunk_context,
                chunk_order=i + 1,
                chunk_type=self._normalize_chunk_type(chunk_data.get('type', 'body'), language),
                overlap_start=self.config.overlap_size if i > 0 else 0,
                overlap_end=self.config.overlap_size if i < len(llm_chunks) - 1 else 0,
                chunk_length=len(chunk_text),
                chunk_word_count=word_count,
                semantic_keywords=keywords,
                content_embedding=content_embedding,
                search_embedding=search_embedding,
                language=language,
                processing_metadata={
                    "llm_summary": chunk_data.get('summary', ''),
                    "chunking_method": "llm_assisted",
                    "model_used": "deepseek" if language == 'zh' else "llama3",
                    "config": self.config.__dict__
                }
            )
            
            story_chunks.append(chunk)
        
        return story_chunks
    
    def _create_context(self, chunk_text: str, all_chunks: List[Dict], current_index: int) -> str:
        """Create extended context around current chunk"""
        context_parts = []
        
        # Add previous chunk if exists
        if current_index > 0:
            prev_chunk = all_chunks[current_index - 1]['text']
            context_parts.append(prev_chunk[-self.config.context_window:])
        
        # Add current chunk
        context_parts.append(chunk_text)
        
        # Add next chunk if exists
        if current_index < len(all_chunks) - 1:
            next_chunk = all_chunks[current_index + 1]['text']
            context_parts.append(next_chunk[:self.config.context_window])
        
        return ' '.join(context_parts) if context_parts else chunk_text
    
    def _normalize_chunk_type(self, chunk_type: str, language: str) -> str:
        """Normalize chunk types across languages"""
        type_mapping = {
            'zh': {
                '開頭': 'opening',
                '發展': 'development', 
                '高潮': 'climax',
                '結尾': 'ending',
                '主體': 'body'
            },
            'en': {
                'opening': 'opening',
                'development': 'development',
                'climax': 'climax', 
                'resolution': 'ending',
                'ending': 'ending',
                'body': 'body'
            }
        }
        
        mapping = type_mapping.get(language, type_mapping['en'])
        return mapping.get(chunk_type.lower(), 'body')

# Example usage
async def main():
    """Example of how to use the chunking pipeline"""
    
    # Sample story content
    sample_story = """
    It was a dark and stormy night when Sarah first heard the whispers. 
    She had been living in the old Victorian house for three months, 
    and everything seemed normal until that night.
    
    The whispers came from the walls, soft at first, then growing louder. 
    Sarah followed the sound upstairs, her heart pounding with each step.
    
    At the end of the hallway stood a figure in white, translucent and ethereal. 
    The ghost turned to face her, its eyes filled with an ancient sadness.
    
    "Help me," it whispered before vanishing into the shadows.
    Sarah knew her peaceful life had changed forever.
    """
    
    # Initialize chunker
    config = ChunkConfig(target_chunk_size=200, max_chunk_size=300)
    chunker = StoryChunker(config)
    
    # Process story
    story_id = str(uuid.uuid4())
    chunks = await chunker.chunk_story(story_id, sample_story, "The Whispers")
    
    # Display results
    print(f"Generated {len(chunks)} chunks:")
    for chunk in chunks:
        print(f"\nChunk {chunk.chunk_order} ({chunk.chunk_type}):")
        print(f"Text: {chunk.chunk_text[:100]}...")
        print(f"Keywords: {chunk.semantic_keywords[:5]}")
        print(f"Language: {chunk.language}")

if __name__ == "__main__":
    asyncio.run(main())