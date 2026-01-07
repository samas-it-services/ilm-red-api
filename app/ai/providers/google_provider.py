"""Google (Gemini) provider implementation.

Supports:
- Gemini 1.5 Flash (fast, long context)
- Gemini 1.5 Pro (balanced, very long context)
- Gemini 2.0 Flash (experimental)
- Text embeddings

API Documentation: https://ai.google.dev/docs
"""

from typing import AsyncIterator

import structlog

from app.ai.base import (
    AIProvider,
    AIProviderError,
    ChatMessage,
    ChatResponse,
    EmbeddingResponse,
    QuotaExceededError,
    RateLimitError,
)
from app.ai import get_model_config

logger = structlog.get_logger(__name__)


class GoogleProvider(AIProvider):
    """Google AI (Gemini) API provider."""

    vendor = "google"
    default_model = "gemini-1.5-flash"
    embedding_model = "text-embedding-004"

    # Embedding pricing per 1M tokens
    EMBEDDING_COST_PER_1M = 0.025

    def __init__(self, api_key: str):
        """Initialize Google provider.

        Args:
            api_key: Google AI API key
        """
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.genai = genai
        except ImportError:
            raise ImportError(
                "google-generativeai package not installed. "
                "Install with: pip install google-generativeai"
            )

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> ChatResponse:
        """Send a chat completion request to Google Gemini.

        Args:
            messages: List of chat messages
            model: Model to use (defaults to gemini-1.5-flash)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)
            system_prompt: Optional system prompt to prepend

        Returns:
            ChatResponse with content and usage statistics
        """
        model = model or self.default_model
        model_config = get_model_config(model)

        # Convert messages to Gemini format
        # Gemini uses "user" and "model" roles
        gemini_messages = []
        system_instruction = system_prompt or ""

        for msg in messages:
            if msg.role == "system":
                system_instruction = f"{system_instruction}\n\n{msg.content}" if system_instruction else msg.content
            elif msg.role == "assistant":
                gemini_messages.append({
                    "role": "model",
                    "parts": [msg.content],
                })
            else:
                gemini_messages.append({
                    "role": "user",
                    "parts": [msg.content],
                })

        try:
            # Create model instance
            generation_config = self.genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )

            gemini_model = self.genai.GenerativeModel(
                model_name=model_config.model_id,
                generation_config=generation_config,
                system_instruction=system_instruction if system_instruction else None,
            )

            # Send request
            response = await gemini_model.generate_content_async(
                gemini_messages,
            )

            # Extract content and usage
            content = response.text if response.text else ""

            # Gemini provides token counts differently
            usage_metadata = getattr(response, "usage_metadata", None)
            prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0) if usage_metadata else 0
            completion_tokens = getattr(usage_metadata, "candidates_token_count", 0) if usage_metadata else 0

            return ChatResponse.from_tokens(
                content=content,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                model_config=model_config,
                finish_reason=response.candidates[0].finish_reason.name if response.candidates else "STOP",
            )

        except Exception as e:
            error_message = str(e)
            logger.error(
                "Google chat error",
                model=model,
                error=error_message,
            )

            if "quota" in error_message.lower() or "429" in error_message:
                raise RateLimitError(
                    message=error_message,
                    vendor=self.vendor,
                    model=model,
                )
            elif "billing" in error_message.lower():
                raise QuotaExceededError(
                    message=error_message,
                    vendor=self.vendor,
                    model=model,
                )
            else:
                raise AIProviderError(
                    message=error_message,
                    vendor=self.vendor,
                    model=model,
                )

    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream a chat completion response from Google Gemini.

        Args:
            messages: List of chat messages
            model: Model to use (defaults to gemini-1.5-flash)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)
            system_prompt: Optional system prompt to prepend

        Yields:
            String chunks of the response as they arrive
        """
        model = model or self.default_model
        model_config = get_model_config(model)

        # Convert messages to Gemini format
        gemini_messages = []
        system_instruction = system_prompt or ""

        for msg in messages:
            if msg.role == "system":
                system_instruction = f"{system_instruction}\n\n{msg.content}" if system_instruction else msg.content
            elif msg.role == "assistant":
                gemini_messages.append({
                    "role": "model",
                    "parts": [msg.content],
                })
            else:
                gemini_messages.append({
                    "role": "user",
                    "parts": [msg.content],
                })

        try:
            generation_config = self.genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )

            gemini_model = self.genai.GenerativeModel(
                model_name=model_config.model_id,
                generation_config=generation_config,
                system_instruction=system_instruction if system_instruction else None,
            )

            # Stream response
            response = await gemini_model.generate_content_async(
                gemini_messages,
                stream=True,
            )

            async for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            error_message = str(e)
            logger.error(
                "Google stream error",
                model=model,
                error=error_message,
            )
            raise AIProviderError(
                message=error_message,
                vendor=self.vendor,
                model=model,
            )

    async def get_embeddings(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> EmbeddingResponse:
        """Generate embeddings using Google.

        Args:
            texts: List of texts to embed
            model: Embedding model to use (defaults to text-embedding-004)

        Returns:
            EmbeddingResponse with embedding vectors
        """
        model = model or self.embedding_model

        try:
            embeddings = []
            total_tokens = 0

            for text in texts:
                result = self.genai.embed_content(
                    model=f"models/{model}",
                    content=text,
                    task_type="retrieval_document",
                )
                embeddings.append(result["embedding"])
                # Estimate tokens (Google doesn't always provide exact count)
                total_tokens += len(text.split()) * 1.3  # Rough estimate

            # Calculate cost
            cost_usd = (total_tokens / 1_000_000) * self.EMBEDDING_COST_PER_1M

            return EmbeddingResponse(
                embeddings=embeddings,
                model=model,
                total_tokens=int(total_tokens),
                cost_usd=cost_usd,
            )

        except Exception as e:
            error_message = str(e)
            logger.error(
                "Google embedding error",
                model=model,
                error=error_message,
            )
            raise AIProviderError(
                message=error_message,
                vendor=self.vendor,
                model=model,
            )
