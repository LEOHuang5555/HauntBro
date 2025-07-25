# Silver Tables Specification - HauntBro ETL

## Table: `silver_stories`

### Purpose

Cleaned and processed stories from bronze layer with extracted metadata, analytics, and quality metrics.

### Schema

| Column | Type | Constraints | Description | How to Derive |
| --- | --- | --- | --- | --- |
| `id` | UUID | PRIMARY KEY | Unique identifier for processed story | `uuid.uuid4()` |
| `source_story_id` | UUID | FOREIGN KEY → bronze_stories(id) | Reference to original bronze story | Direct from bronze_stories.id |
| `title` | VARCHAR(500) | NOT NULL | Cleaned story title | Clean bronze title, remove extra whitespace |
| `cleaned_content` | TEXT | NOT NULL | Processed story content | Apply content cleaning pipeline |
| `original_content_hash` | VARCHAR(64) | UNIQUE | SHA-256 hash for deduplication | `hashlib.sha256(original_content.encode()).hexdigest()` |
| `author` | VARCHAR(100) |  | Story author name | From bronze_stories.author, handle [deleted] |
| `source` | VARCHAR(50) | NOT NULL | Data source platform | 'reddit_nosleep', 'ptt_marvel', etc. |
| `source_url` | VARCHAR(1000) |  | Original post URL | From bronze_stories.source_url |
| `post_date` | TIMESTAMP WITH TIME ZONE |  | Original publication date | From bronze_stories.post_date |
| `tags` | TEXT[] |  | Extracted categorical tags | Parse from title: [創作], [經驗], [新聞] |
| `story_type` | VARCHAR(20) |  | Primary story category | Map tags to types: '創作'→'fiction', '經驗'→'experience' |
| `language` | VARCHAR(10) |  | Detected primary language | Language detection algorithm |
| `reading_time_minutes` | INTEGER | CHECK > 0 | Estimated reading time | Calculate from word count and language |
| `word_count` | INTEGER | CHECK >= 0 | Total word count | Count algorithm based on language |
| `character_count` | INTEGER | CHECK >= 0 | Total character count | `len(cleaned_content)` |
| `content_quality_score` | DECIMAL(3,2) | CHECK 0.00-1.00 | Content quality assessment | ML model or heuristic scoring |
| `is_complete` | BOOLEAN | DEFAULT TRUE | Story completion status | Detect if part of series/incomplete |
| `series_info` | JSONB |  | Series metadata if applicable | Extract part numbers, series name |
| `processing_status` | VARCHAR(20) | DEFAULT 'processed' | ETL processing status | 'processed', 'failed', 'pending' |
| `created_at` | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | Record creation time | System timestamp |
| `updated_at` | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | Last update time | System timestamp on updates |

### Derivation Methods

### Content Cleaning (`cleaned_content`)

```python
def clean_content(raw_content: str) -> str:
    # Remove Reddit-specific formatting
    content = re.sub(r'\*\*([^*]+)\*\*', r'\1', raw_content)  # Remove bold
    content = re.sub(r'\*([^*]+)\*', r'\1', content)          # Remove italics
    content = re.sub(r'^\s*&gt;', '>', content, flags=re.MULTILINE)  # Fix quotes

    # Remove excessive whitespace
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)      # Max 2 newlines
    content = re.sub(r'[ \t]+', ' ', content)                # Normalize spaces

    # Remove common Reddit footers
    content = re.sub(r'\n\s*---+\s*\n.*$', '', content, flags=re.DOTALL)
    content = re.sub(r'\n\s*Edit:.*$', '', content, flags=re.DOTALL)

    return content.strip()

```

### Tag Extraction (`tags`, `story_type`)

```python
def extract_tags_and_type(title: str) -> Tuple[List[str], str]:
    # Extract tags in brackets
    tag_pattern = r'\[([^\]]+)\]'
    tags = re.findall(tag_pattern, title, re.IGNORECASE)

    # Normalize tags
    normalized_tags = []
    story_type = 'unknown'

    for tag in tags:
        tag_clean = tag.strip().lower()
        if tag_clean in ['創作', 'creation', 'fiction']:
            normalized_tags.append('fiction')
            story_type = 'fiction'
        elif tag_clean in ['經驗', 'experience', 'true']:
            normalized_tags.append('experience')
            story_type = 'experience'
        elif tag_clean in ['新聞', 'news']:
            normalized_tags.append('news')
            story_type = 'news'
        else:
            normalized_tags.append(tag_clean)

    return normalized_tags, story_type

```

### Language Detection (`language`)

```python
from langdetect import detect, LangDetectError

def detect_language(content: str) -> str:
    try:
        # Check character composition
        chinese_chars = len([c for c in content if '\u4e00' <= c <= '\u9fff'])
        total_chars = len(content.replace(' ', ''))

        if chinese_chars / total_chars > 0.3:
            return 'zh'  # Chinese dominant

        detected = detect(content)
        return detected if detected in ['en', 'zh'] else 'mixed'
    except LangDetectError:
        return 'unknown'

```

### Reading Time Calculation (`reading_time_minutes`)

```python
def calculate_reading_time(content: str, language: str, story_type: str) -> int:
    if language == 'zh':
        # Chinese reading speed: ~300-400 characters per minute
        chars = len([c for c in content if '\u4e00' <= c <= '\u9fff'])
        base_time = max(1, round(chars / 350))
    else:
        # English reading speed: ~200-250 words per minute
        words = len(content.split())
        base_time = max(1, round(words / 225))

    # Adjust for story type
    multipliers = {
        'fiction': 1.2,    # Slower, more immersive
        'news': 0.8,       # Faster, factual
        'experience': 1.0   # Normal pace
    }

    return round(base_time * multipliers.get(story_type, 1.0))

```

### Word Count (`word_count`)

```python
def count_words(content: str, language: str) -> int:
    if language == 'zh':
        # Count Chinese characters + English words
        chinese_chars = len([c for c in content if '\u4e00' <= c <= '\u9fff'])
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', content))
        return chinese_chars + english_words
    else:
        # Standard word count
        return len(content.split())

```

### Quality Score (`content_quality_score`)

```python
def assess_content_quality(content: str) -> float:
    score = 1.0

    # Length penalties
    if len(content) < 100:
        score *= 0.5  # Too short
    elif len(content) > 50000:
        score *= 0.8  # Extremely long

    # Structure assessment
    paragraphs = content.split('\n\n')
    if len(paragraphs) < 2:
        score *= 0.7  # Poor structure

    # Repetition check
    sentences = content.split('.')
    unique_ratio = len(set(sentences)) / len(sentences) if sentences else 0
    score *= max(0.5, unique_ratio)

    # Character diversity
    char_diversity = len(set(content.lower())) / len(content) if content else 0
    score *= max(0.5, char_diversity * 10)

    return round(min(1.0, max(0.0, score)), 2)

```

---

## Table: `silver_story_chunks`

### Purpose

Segmented story chunks optimized for vector embedding and semantic search, with overlapping context for better retrieval.

### Schema

| Column | Type | Constraints | Description | How to Derive |
| --- | --- | --- | --- | --- |
| `id` | UUID | PRIMARY KEY | Unique chunk identifier | `uuid.uuid4()` |
| `story_id` | UUID | FOREIGN KEY → silver_stories(id) | Parent story reference | From silver_stories.id |
| `chunk_text` | TEXT | NOT NULL | Main chunk content for embedding | Intelligent chunking algorithm |
| `chunk_context` | TEXT | NOT NULL | Extended context around chunk | Chunk + surrounding context |
| `chunk_order` | INTEGER | NOT NULL | Sequential position in story | 1, 2, 3... based on original order |
| `chunk_type` | VARCHAR(20) |  | Chunk position classification | 'opening', 'body', 'climax', 'ending' |
| `overlap_start` | INTEGER | DEFAULT 0 | Characters overlapping with previous | Count of overlapping characters |
| `overlap_end` | INTEGER | DEFAULT 0 | Characters overlapping with next | Count of overlapping characters |
| `content_embedding` | VECTOR(768) |  | Dense vector for similarity search | OpenAI/Sentence-BERT embedding |
| `search_embedding` | VECTOR(768) |  | Optimized vector for search queries | Query-optimized embedding model |
| `chunk_length` | INTEGER | CHECK > 0 | Character count of chunk_text | `len(chunk_text)` |
| `chunk_word_count` | INTEGER | CHECK >= 0 | Word count of chunk_text | Word counting by language |
| `semantic_keywords` | TEXT[] |  | Extracted key terms/entities | NLP keyword extraction |
| `embedding_model` | VARCHAR(100) | NOT NULL | Model used for embeddings | 'text-embedding-ada-002', etc. |
| `embedding_version` | VARCHAR(20) | NOT NULL | Model version identifier | '2023-12-01', etc. |
| `created_at` | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | Chunk creation time | System timestamp |

### Derivation Methods

### Intelligent Chunking (`chunk_text`, `chunk_context`)

```python
def create_story_chunks(story_content: str, target_size: int = 500, overlap: int = 50) -> List[Dict]:
    # Split by sentences to maintain coherence
    sentences = sent_tokenize(story_content)
    chunks = []
    current_chunk = []
    current_length = 0

    for i, sentence in enumerate(sentences):
        sentence_length = len(sentence)

        if current_length + sentence_length > target_size and current_chunk:
            # Create chunk with overlap
            chunk_text = ' '.join(current_chunk)

            # Add context (previous and next sentences)
            context_start = max(0, i - 3)
            context_end = min(len(sentences), i + 3)
            chunk_context = ' '.join(sentences[context_start:context_end])

            chunks.append({
                'chunk_text': chunk_text,
                'chunk_context': chunk_context,
                'chunk_order': len(chunks) + 1,
                'overlap_start': overlap if chunks else 0,
                'overlap_end': overlap,
                'chunk_length': len(chunk_text)
            })

            # Start new chunk with overlap
            overlap_sentences = current_chunk[-2:] if len(current_chunk) >= 2 else current_chunk
            current_chunk = overlap_sentences + [sentence]
            current_length = sum(len(s) for s in current_chunk)
        else:
            current_chunk.append(sentence)
            current_length += sentence_length

    # Handle final chunk
    if current_chunk:
        chunk_text = ' '.join(current_chunk)
        chunks.append({
            'chunk_text': chunk_text,
            'chunk_context': chunk_text,  # No additional context for final chunk
            'chunk_order': len(chunks) + 1,
            'overlap_start': overlap if chunks else 0,
            'overlap_end': 0,
            'chunk_length': len(chunk_text)
        })

    return chunks

```

### Chunk Type Classification (`chunk_type`)

```python
def classify_chunk_type(chunk_order: int, total_chunks: int, chunk_text: str) -> str:
    # Position-based classification
    if chunk_order == 1:
        return 'opening'
    elif chunk_order == total_chunks:
        return 'ending'

    # Content-based hints
    chunk_lower = chunk_text.lower()

    # Climax indicators
    climax_keywords = ['suddenly', '突然', 'scream', '尖叫', 'blood', '血', 'death', '死']
    if any(keyword in chunk_lower for keyword in climax_keywords):
        return 'climax'

    return 'body'

```

### Vector Embeddings (`content_embedding`, `search_embedding`)

```python
import openai
from sentence_transformers import SentenceTransformer

def generate_embeddings(chunk_text: str, chunk_context: str) -> Tuple[List[float], List[float]]:
    # Content embedding - for similarity and clustering
    content_embedding = openai.Embedding.create(
        input=chunk_context,  # Use full context for richer embedding
        model="text-embedding-ada-002"
    )['data'][0]['embedding']

    # Search embedding - optimized for query matching
    search_model = SentenceTransformer('all-MiniLM-L6-v2')
    search_embedding = search_model.encode(chunk_text).tolist()

    return content_embedding, search_embedding

```

### Semantic Keywords (`semantic_keywords`)

```python
from transformers import AutoTokenizer, AutoModelForTokenClassification
import spacy

def extract_semantic_keywords(chunk_text: str, language: str) -> List[str]:
    keywords = []

    if language == 'zh':
        # Chinese NER and keyword extraction
        nlp = spacy.load('zh_core_web_sm')
        doc = nlp(chunk_text)

        # Extract named entities
        entities = [ent.text for ent in doc.ents if ent.label_ in ['PERSON', 'GPE', 'ORG']]
        keywords.extend(entities)

        # Extract key nouns and verbs
        key_pos = [token.text for token in doc if token.pos_ in ['NOUN', 'VERB'] and len(token.text) > 1]
        keywords.extend(key_pos[:10])  # Top 10

    else:
        # English keyword extraction
        nlp = spacy.load('en_core_web_sm')
        doc = nlp(chunk_text)

        entities = [ent.text for ent in doc.ents]
        keywords.extend(entities)

        # Key terms
        key_terms = [token.lemma_ for token in doc if token.pos_ in ['NOUN', 'VERB'] and not token.is_stop]
        keywords.extend(key_terms[:10])

    return list(set(keywords))  # Remove duplicates

```

### Usage Examples

### Inserting into silver_stories

```sql
INSERT INTO silver_stories (
    id, source_story_id, title, cleaned_content, original_content_hash,
    author, source, source_url, post_date, tags, story_type, language,
    reading_time_minutes, word_count, character_count, content_quality_score,
    is_complete, series_info
) VALUES (
    gen_random_uuid(),
    $1, -- bronze story id
    $2, -- cleaned title
    $3, -- cleaned content
    $4, -- content hash
    $5, -- author
    $6, -- source
    $7, -- source url
    $8, -- post date
    $9, -- tags array
    $10, -- story type
    $11, -- language
    $12, -- reading time
    $13, -- word count
    $14, -- character count
    $15, -- quality score
    $16, -- is complete
    $17  -- series info json
);

```

### Inserting into silver_story_chunks

```sql
INSERT INTO silver_story_chunks (
    id, story_id, chunk_text, chunk_context, chunk_order, chunk_type,
    overlap_start, overlap_end, content_embedding, search_embedding,
    chunk_length, chunk_word_count, semantic_keywords,
    embedding_model, embedding_version
) VALUES (
    gen_random_uuid(),
    $1, -- story id
    $2, -- chunk text
    $3, -- chunk context
    $4, -- chunk order
    $5, -- chunk type
    $6, -- overlap start
    $7, -- overlap end
    $8, -- content embedding vector
    $9, -- search embedding vector
    $10, -- chunk length
    $11, -- chunk word count
    $12, -- semantic keywords array
    $13, -- embedding model
    $14  -- embedding version
);

```

This specification provides a complete framework for transforming raw ghost stories into searchable, analyzable chunks with rich metadata and semantic understanding.