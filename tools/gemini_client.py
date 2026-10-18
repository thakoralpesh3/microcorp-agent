"""
MicroCorp AI - Gemini LLM Client
Provides multi-model automatic fallback cascade, retry handling, and token usage accounting.
"""

import time
import logging
from typing import Tuple, Optional, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import GEMINI_API_KEY, LLM_MODELS
from google import genai
from google.genai import errors

logger = logging.getLogger("MicroCorp.GeminiClient")

class GeminiLLMClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.client = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize GenAI client: {e}")
        self.active_model = LLM_MODELS[0]

    def set_api_key(self, key: str):
        self.api_key = key.strip()
        self.client = genai.Client(api_key=self.api_key)

    def generate(self, prompt: str, system_instruction: Optional[str] = None, candidate_models: Optional[List[str]] = None) -> Tuple[str, int, int]:
        """
        Executes generation across candidate models in fallback order.
        Returns: (generated_text, prompt_tokens, candidate_tokens)
        """
        if not self.client:
            raise ValueError("Gemini API Key is not configured. Please supply a GEMINI_API_KEY.")

        models_to_try = candidate_models or LLM_MODELS
        last_error = None

        config_params = {}
        if system_instruction:
            config_params["system_instruction"] = system_instruction

        for model_name in models_to_try:
            try:
                # Add small sleep to respect rate limits
                time.sleep(0.2)
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config_params if config_params else None
                )
                self.active_model = model_name
                
                # Extract token usage
                p_tokens = 0
                c_tokens = 0
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    p_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                    c_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

                text = response.text or ""
                return text, p_tokens, c_tokens

            except (errors.ClientError, errors.APIError, Exception) as e:
                last_error = e
                # If quota exhausted (429) or model not found (404), fall back to next model
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "404" in err_str:
                    logger.warning(f"Model {model_name} unavailable ({err_str[:60]}...). Falling back to next candidate.")
                    continue
                else:
                    logger.error(f"Generation error with {model_name}: {e}")
                    continue

        raise RuntimeError(f"All Gemini model candidates failed. Last error: {last_error}")

# Global LLM instance
llm_client = GeminiLLMClient()
