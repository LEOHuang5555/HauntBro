
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