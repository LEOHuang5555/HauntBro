import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import os
from pathlib import Path

class ModelManager:
    def __init__(self, cache_dir="./models"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        
        # Configure quantization for memory efficiency
        self.bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16
        )
    
    def setup_llama_english(self):
        """Setup LLaMA for English content"""
        model_name = "meta-llama/Llama-2-7b-chat-hf"
        
        print("Loading LLaMA tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=self.cache_dir,
            trust_remote_code=True
        )
        
        print("Loading LLaMA model...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=self.bnb_config,
            device_map="auto",
            cache_dir=self.cache_dir,
            trust_remote_code=True,
            torch_dtype=torch.float16
        )
        
        return tokenizer, model
    
    def setup_deepseek_mandarin(self):
        """Setup Deepseek for Mandarin content"""
        model_name = "deepseek-ai/deepseek-coder-6.7b-instruct"
        
        print("Loading Deepseek tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=self.cache_dir,
            trust_remote_code=True
        )
        
        print("Loading Deepseek model...")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=self.bnb_config,
            device_map="auto",
            cache_dir=self.cache_dir,
            trust_remote_code=True,
            torch_dtype=torch.float16
        )
        
        return tokenizer, model

def main():
    """Test model setup"""
    manager = ModelManager()
    
    try:
        # Test LLaMA
        print("Setting up LLaMA...")
        llama_tokenizer, llama_model = manager.setup_llama_english()
        print("✅ LLaMA setup successful!")
        
        # Test Deepseek  
        print("Setting up Deepseek...")
        deepseek_tokenizer, deepseek_model = manager.setup_deepseek_mandarin()
        print("✅ Deepseek setup successful!")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        print("Consider using Ollama for easier model management")

if __name__ == "__main__":
    main()