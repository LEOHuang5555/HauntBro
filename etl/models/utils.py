import re
import jieba
import requests

from typing import List

from etl.config.config import CONFIG



def parse_title_tags(title: str) -> List[str]:
    """Extract structured tags from a horror story title."""
    tags = []

    # Step 1: 擷取像 [創作]、（經驗）這種標籤
    # 使用較安全的 regex，支援常見中英文括號，並避免語法錯誤
    tag_match = re.match(r"^[\[\(【（]{1}([^()\[\]【】（）]{1,6})[\]\)】）]{1}", title)
    if tag_match:
        prefix = tag_match.group(1).strip()
        if 1 < len(prefix) <= 6:
            tags.append(prefix)

    # Step 2: 去除開頭的 Re: FW: 或 [xxx]
    clean_title = re.sub(r"(?i)^(Re|FW)\s*:\s*", "", title)
    clean_title = re.sub(r"^[\[\(（【][^\]\)）】]+[\]\)）】]\s*", "", clean_title)

    # Step 3: jieba 斷詞取前3詞
    title_words = [w for w in jieba.cut(clean_title) if len(w.strip()) > 1]
    tags.extend(title_words[:3])  # 最多取前3詞

    return list(set(tags))



async def send_prompt_to_LLM(prompts,
                       model_name=CONFIG['model'].english_model,
                       timeout: int = 180,
                       temperature: float = 0.3,
                       top_p: float = 0.8,
                       num_predict: int = 1024,
                       max_retry: int = 3) -> str:
    """Send prompt to Ollama with retry logic"""
    for attempt in range(max_retry):
        try:
            response = requests.post(
                f"{CONFIG['model'].ollama_base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompts,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "top_p": top_p,
                        "num_predict": num_predict
                    }
                },
                timeout=timeout
            )
            response.raise_for_status()
            return response.json().get("response", "")

        except Exception as e:
            print(f"⚠️ LLM request failed (attempt {attempt + 1}): {e}")
            if attempt == max_retry - 1:
                raise

    return ""
