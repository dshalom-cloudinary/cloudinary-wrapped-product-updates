"""OpenAI LLM client for Slack Wrapped.

Provides robust OpenAI API integration with retry logic and fallback.
"""

import os
import time
import logging
from typing import Optional
from dataclasses import dataclass

from openai import OpenAI, OpenAIError, APITimeoutError, RateLimitError

logger = logging.getLogger(__name__)


@dataclass
class LLMUsage:
    """Token usage tracking."""
    
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def add(self, prompt: int, completion: int):
        """Add usage from a response."""
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion


class LLMClient:
    """OpenAI API client with retry logic and fallback."""
    
    DEFAULT_MODEL = "gpt-5.2"
    DEV_MODEL = "gpt-5-mini"
    
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 60,
    ):
        """
        Initialize LLM client.
        
        Args:
            model: OpenAI model to use
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
        """
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self.usage = LLMUsage()
        
        # Get API key
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = OpenAI(api_key=api_key)
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Creativity parameter (0-2)
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated text response
            
        Raises:
            LLMError: If generation fails after all retries
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self.timeout,
                )
                
                # Track usage
                if response.usage:
                    self.usage.add(
                        response.usage.prompt_tokens,
                        response.usage.completion_tokens,
                    )
                
                return response.choices[0].message.content or ""
                
            except RateLimitError as e:
                last_error = e
                wait_time = self._get_retry_wait(attempt)
                logger.warning(
                    f"Rate limited, waiting {wait_time}s before retry "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                time.sleep(wait_time)
                
            except APITimeoutError as e:
                last_error = e
                logger.warning(
                    f"Request timeout, retrying "
                    f"(attempt {attempt + 1}/{self.max_retries})"
                )
                # No wait for timeout, just retry
                
            except OpenAIError as e:
                last_error = e
                logger.error(f"OpenAI API error: {e}")
                wait_time = self._get_retry_wait(attempt)
                time.sleep(wait_time)
        
        raise LLMError(
            f"Failed to generate response after {self.max_retries} attempts: {last_error}"
        )
    
    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 2000,
    ) -> str:
        """
        Generate a JSON response from the LLM.
        
        Uses lower temperature for more consistent JSON output.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Creativity parameter (default lower for JSON)
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated JSON string
        """
        json_system = (system_prompt or "") + (
            "\n\nYou must respond with valid JSON only. No markdown, no explanation, "
            "just the JSON object."
        )
        
        return self.generate(
            prompt=prompt,
            system_prompt=json_system.strip(),
            temperature=temperature,
            max_tokens=max_tokens,
        )
    
    def _get_retry_wait(self, attempt: int) -> float:
        """Get wait time with exponential backoff."""
        # 1s, 2s, 4s, 8s, 16s (capped at 30s)
        return min(2 ** attempt, 30)
    
    def get_usage(self) -> LLMUsage:
        """Get cumulative token usage."""
        return self.usage
    
    def get_estimated_cost(self) -> float:
        """
        Get estimated cost based on usage.
        
        Note: Uses approximate pricing as of 2025. Actual costs may vary.
        OpenAI pricing changes frequently - check https://openai.com/pricing
        for current rates.
        
        Returns:
            Estimated cost in USD (approximate)
        """
        # Approximate pricing per 1M tokens (as of 2025)
        # These rates are estimates and may not reflect current pricing
        if "mini" in self.model.lower():
            input_rate = 0.25 / 1_000_000
            output_rate = 2.00 / 1_000_000
        else:
            input_rate = 1.75 / 1_000_000
            output_rate = 14.00 / 1_000_000
        
        return (
            self.usage.prompt_tokens * input_rate +
            self.usage.completion_tokens * output_rate
        )


class LLMError(Exception):
    """Raised when LLM generation fails."""
    pass


def create_llm_client(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    use_dev_model: bool = False,
) -> LLMClient:
    """
    Factory function to create LLM client.
    
    Args:
        model: Optional model override
        api_key: Optional API key override
        use_dev_model: Use cheaper dev model
        
    Returns:
        Configured LLMClient instance
    """
    if model is None:
        model = LLMClient.DEV_MODEL if use_dev_model else LLMClient.DEFAULT_MODEL
    
    return LLMClient(model=model, api_key=api_key)
