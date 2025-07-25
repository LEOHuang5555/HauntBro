"""
English Text Processor - LLaMA Integration  
Handles English ghost story processing with LLaMA models
"""

import asyncio
import torch
import re
import json
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import spacy
from pathlib import Path
import sys

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from etl.processing.config import CONFIG

# Transformers imports for LLaMA
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

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
    """English text chunk with narrative context"""
    chunk_id: str
    original_text: str
    processed_text: str
    chunk_order: int
    chunk_type: str  # 'opening', 'body', 'climax', 'ending'
    word_count: int
    sentence_count: int
    semantic_keywords: List[str]
    narrative_elements: List[str]  # Character, setting, plot elements
    horror_indicators: List[str]  # Fear, suspense, horror elements
    dialogue_ratio: float  # Percentage of text that is dialogue
    processing_metadata: Dict[str, Any]


@dataclass
class ProcessingResult:
    """Result of English text processing"""
    success: bool
    chunks: List[EnglishChunk]
    processing_time_ms: int
    model_cost: float
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None


class EnglishProcessor:
    """
    LLaMA-powered English text processor for ghost stories
    Handles narrative structure preservation, dialogue detection, and semantic chunking
    """
    
    def __init__(self, cache_dir: str = "./models"):
        """Initialize English processor with LLaMA model"""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Model configuration
        self.model_config = CONFIG["model"]
        self.chunking_config = CONFIG["chunking"]
        
        # LLaMA model setup
        self.tokenizer = None
        self.model = None
        self.is_initialized = False
        
        # English processing setup
        self._setup_english_processors()
        
        # Cost tracking
        self.total_cost = 0.0
        self.processing_stats = {
            'total_processed': 0,
            'total_chunks': 0,
            'avg_processing_time': 0.0,
            'errors': 0
        }
    
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
        """Initialize LLaMA model for English processing"""
        if not TRANSFORMERS_AVAILABLE:
            print("❌ Transformers library not available")
            return False
        
        try:
            print("🚀 Initializing LLaMA model for English processing...")
            
            # LLaMA model configuration - using Llama-2 7B chat model
            model_name = "meta-llama/Llama-2-7b-chat-hf"
            
            # Configure quantization for memory efficiency
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16
            )
            
            print("Loading LLaMA tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                cache_dir=self.cache_dir,
                trust_remote_code=True
            )
            
            # Add padding token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            print("Loading LLaMA model...")
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=bnb_config,
                device_map="auto",
                cache_dir=self.cache_dir,
                trust_remote_code=True,
                torch_dtype=torch.float16
            )
            
            self.is_initialized = True
            print(f"✅ LLaMA model loaded on {self.device}")
            return True
            
        except Exception as e:
            print(f"❌ LLaMA initialization failed: {e}")
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
    
    def extract_narrative_elements(self, text: str) -> List[str]:
        """Extract narrative elements like characters, settings, plot devices"""
        elements = []
        
        # Character indicators
        character_patterns = [
            r'\b(I|me|my|myself|we|us|our)\b',  # First person
            r'\b(he|she|him|her|his|hers|they|them|their)\b',  # Third person
            r'\b[A-Z][a-z]+\b(?:\s+[A-Z][a-z]+)*',  # Proper names
        ]
        
        # Setting indicators  
        setting_patterns = [
            r'\b(house|home|school|hospital|church|cemetery|forest|basement|attic|bedroom|bathroom)\b',
            r'\b(night|midnight|dark|darkness|shadow|moonlight|candlelight)\b',
            r'\b(old|abandoned|empty|haunted|creepy|eerie)\b'
        ]
        
        # Plot device indicators
        plot_patterns = [
            r'\b(suddenly|then|meanwhile|later|earlier|before|after)\b',
            r'\b(heard|saw|felt|noticed|realized|discovered|found)\b',
            r'\b(door|footsteps|voice|whisper|scream|cry|knock)\b'
        ]
        
        all_patterns = character_patterns + setting_patterns + plot_patterns
        
        for pattern in all_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            elements.extend(matches)
        
        # Remove duplicates and common words
        unique_elements = []
        for element in set(elements):
            if element.lower() not in self.stop_words and len(element) > 2:
                unique_elements.append(element.lower())
        
        return unique_elements[:10]  # Return top 10
    
    def extract_horror_indicators(self, text: str) -> List[str]:
        """Extract horror and suspense indicators"""
        indicators = []
        
        # Fear and horror keywords
        horror_patterns = [
            # Direct fear words
            r'\b(scared|afraid|terrified|horrified|petrified|frightened)\b',
            # Physical reactions  
            r'\b(shaking|trembling|shivering|goosebumps|chills|froze|frozen)\b',
            # Atmospheric descriptions
            r'\b(creepy|eerie|sinister|ominous|menacing|ghostly|haunting)\b',
            # Sensory horror
            r'\b(cold|chill|darkness|silence|shadow|whisper|moan|howl)\b',
            # Gore and violence (mild)
            r'\b(blood|bleeding|wound|death|dead|corpse|grave)\b'
        ]
        
        for pattern in horror_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            indicators.extend([match.lower() for match in matches])
        
        return list(set(indicators))[:8]  # Return unique, limit to 8
    
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
        """Extract keywords using NLTK"""
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
    
    async def chunk_story_with_llama(self, story_text: str, title: str = "") -> List[EnglishChunk]:
        """
        Use LLaMA to intelligently chunk English ghost stories
        Preserves narrative structure and character development
        """
        if not self.is_initialized:
            raise RuntimeError("English processor not initialized - call initialize() first")
        
        start_time = datetime.now()
        chunks = []
        
        try:
            # Normalize the text first
            normalized_text = self.normalize_english_text(story_text)
            
            # Create chunking prompt for LLaMA
            chunking_prompt = f"""[INST] You are a professional text analyst specializing in horror stories and ghost narratives. 
Please intelligently segment the following story to preserve narrative flow and character development.

Story Title: {title}
Story Content: {normalized_text}

Requirements:
1. Each chunk should be approximately {self.chunking_config.target_chunk_size} words
2. Break at natural paragraph or scene transitions
3. Preserve the horror atmosphere and suspense
4. Label each chunk type: opening/development/climax/ending

Please respond in JSON format with a "chunks" array, where each chunk contains:
- text: the chunk content
- type: chunk type
- order: sequence number
- keywords: list of key terms

[/INST]"""
            
            # Tokenize the prompt
            inputs = self.tokenizer.encode(
                chunking_prompt, 
                return_tensors="pt", 
                max_length=4096,
                truncation=True
            ).to(self.device)
            
            # Generate response with LLaMA
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
            
            # Parse JSON response from LLaMA
            try:
                chunk_data = json.loads(response_text)
                llama_chunks = chunk_data.get('chunks', [])
            except json.JSONDecodeError:
                print("⚠️  LLaMA response not valid JSON, falling back to rule-based chunking")
                llama_chunks = []
            
            # If LLaMA chunking fails, use fallback method
            if not llama_chunks:
                llama_chunks = self._fallback_chunking(normalized_text)
            
            # Process each chunk
            for i, chunk_info in enumerate(llama_chunks):
                chunk_text = chunk_info.get('text', '').strip()
                if not chunk_text:
                    continue
                
                # Extract metadata
                narrative_elements = self.extract_narrative_elements(chunk_text)
                horror_indicators = self.extract_horror_indicators(chunk_text)
                keywords = chunk_info.get('keywords', [])
                if not keywords:  # Fallback keyword extraction
                    keywords = self.extract_keywords_nltk(chunk_text)
                
                # Calculate metrics
                word_count = len(chunk_text.split())
                sentence_count = len(sent_tokenize(chunk_text)) if NLTK_AVAILABLE else chunk_text.count('.') + chunk_text.count('!') + chunk_text.count('?')
                dialogue_ratio = self.calculate_dialogue_ratio(chunk_text)
                
                chunk = EnglishChunk(
                    chunk_id=f"en_chunk_{i+1}",
                    original_text=chunk_text,
                    processed_text=chunk_text,  # Already normalized
                    chunk_order=i + 1,
                    chunk_type=chunk_info.get('type', 'body').lower(),
                    word_count=word_count,
                    sentence_count=sentence_count,
                    semantic_keywords=keywords[:10],  # Limit to top 10
                    narrative_elements=narrative_elements[:8],  # Limit to top 8
                    horror_indicators=horror_indicators[:8],  # Limit to top 8
                    dialogue_ratio=dialogue_ratio,
                    processing_metadata={
                        'model_used': 'llama3.2',
                        'processing_time': (datetime.now() - start_time).total_seconds(),
                        'normalization_applied': True,
                        'keyword_extraction_method': 'nltk' if NLTK_AVAILABLE else 'regex'
                    }
                )
                
                chunks.append(chunk)
            
            # Calculate cost (estimate based on tokens)
            total_tokens = len(inputs[0]) + sum(len(self.tokenizer.encode(chunk.processed_text)) for chunk in chunks)
            estimated_cost = self._calculate_processing_cost(total_tokens)
            self.total_cost += estimated_cost
            
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
                processed_text=chunk_text,
                chunk_order=chunk_id,
                chunk_type='body',
                word_count=len(chunk_words),
                sentence_count=chunk_text.count('.') + chunk_text.count('!') + chunk_text.count('?'),
                semantic_keywords=[],
                narrative_elements=[],
                horror_indicators=[],
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
    
    def _calculate_processing_cost(self, total_tokens: int) -> float:
        """Calculate estimated processing cost for LLaMA usage"""
        # Estimated cost per 1K tokens (adjust based on actual pricing)
        cost_per_1k_tokens = 0.003  # $0.003 per 1K tokens (estimate for LLaMA)
        return (total_tokens / 1000) * cost_per_1k_tokens
    
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
            # Chunk the story using LLaMA
            chunks = await self.chunk_story_with_llama(story_text, title)
            
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
                self._calculate_processing_cost(chunk.word_count * 1.3)  # Estimate tokens from words
                for chunk in chunks
            )
            
            result = ProcessingResult(
                success=True,
                chunks=chunks,
                processing_time_ms=processing_time_ms,
                model_cost=total_cost,
                metadata={
                    'language': 'en',
                    'total_words': len(story_text.split()),
                    'chunks_generated': len(chunks),
                    'model_used': 'llama3.2',
                    'normalization_applied': True,
                    'avg_dialogue_ratio': sum(chunk.dialogue_ratio for chunk in chunks) / len(chunks) if chunks else 0,
                    'narrative_elements_found': sum(len(chunk.narrative_elements) for chunk in chunks),
                    'horror_indicators_found': sum(len(chunk.horror_indicators) for chunk in chunks)
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
                model_cost=0.0,
                error_message=error_msg
            )
    
    def get_processing_stats(self) -> Dict:
        """Get comprehensive processing statistics"""
        return {
            'processor_type': 'english_llama',
            'model_name': 'llama3.2',
            'device': self.device,
            'is_initialized': self.is_initialized,
            'total_cost': self.total_cost,
            'processing_stats': self.processing_stats,
            'nltk_available': NLTK_AVAILABLE,
            'transformers_available': TRANSFORMERS_AVAILABLE
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.model:
            del self.model
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
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
                print(f"   Estimated cost: ${result.model_cost:.4f}")
                
                for i, chunk in enumerate(result.chunks[:3]):  # Show first 3 chunks
                    print(f"\n📝 Chunk {i+1} ({chunk.chunk_type}):")
                    print(f"   Text: {chunk.processed_text[:100]}...")
                    print(f"   Keywords: {chunk.semantic_keywords}")
                    print(f"   Narrative elements: {chunk.narrative_elements}")
                    print(f"   Horror indicators: {chunk.horror_indicators}")
                    print(f"   Dialogue ratio: {chunk.dialogue_ratio:.2%}")
            else:
                print(f"❌ Processing failed: {result.error_message}")
        
    finally:
        await processor.cleanup()


if __name__ == "__main__":
    asyncio.run(main())