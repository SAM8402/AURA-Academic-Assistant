import logging
from typing import Tuple, List, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings

logger = logging.getLogger(__name__)

def build_robust_llm(temperature: float = 0.7, max_retries: int = 1) -> Tuple[Any, List[str]]:
    """
    Builds a robust LLM instance using a multi-model fallback chain from settings.
    
    Returns:
        Tuple containing:
        - The primary LLM instance with fallbacks configured (or None if missing keys).
        - A list of the parsed model names that were configured.
    """
    api_keys = [k.strip() for k in settings.GOOGLE_API_KEY.split(",") if k.strip()]
    if not api_keys:
        api_keys = [""]
        
    models = [m.strip() for m in settings.LLM_FALLBACK_CHAIN.split(",") if m.strip()]
    if not models:
        # Failsafe default
        models = [
            "gemini-3.0-flash", 
            "gemini-3-flash-preview", 
            "gemini-3.1-flash-lite", 
            "gemini-3.1-flash-lite-preview", 
            "gemini-2.5-flash", 
            "gemini-2.5-flash-lite", 
            "gemma-3-27b", 
            "gemma-3-27b-it"
        ]
        
    llms = []
    
    for model_name in models:
        for key in api_keys:
            if not key or key == "your-google-api-key":
                continue # Skip invalid keys if any
                
            llms.append(
                ChatGoogleGenerativeAI(
                    model=model_name,
                    google_api_key=key,
                    temperature=temperature,
                    max_retries=max_retries,
                )
            )
            
    if not llms:
        return None, models
        
    return llms[0].with_fallbacks(llms[1:]), models
