"""OpenAI provider implementation.

Supports:
- GPT-4o, GPT-4o-mini, GPT-4 Turbo
- O1 models (reasoning)
- Text embeddings (text-embedding-3-small, text-embedding-3-large)
"""

from typing import AsyncIterator

import structlog
from openai import AsyncOpenAI

from app.ai.base import (
    AIProvider,
    AIProviderError,
    ChatMessage,
    ChatResponse,
    EmbeddingResponse,
    ModelNotAvailableError,
    QuotaExceededError,
    RateLimitError,
)
from app.ai import MODEL_REGISTRY, get_model_config

logger = structlog.get_logger(__name__)


class OpenAIProvider(AIProvider):
    """OpenAI API provider."""

    vendor = "openai"
    default_model = "gpt-4o-mini"
    embedding_model = "text-embedding-3-small"

    # Embedding model pricing per 1M tokens
    EMBEDDING_PRICING = {
        "text-embedding-3-small": 0.02,
        "text-embedding-3-large": 0.13,
        "text-embedding-ada-002": 0.10,
    }

    def __init__(self, api_key: str):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
        """
        self.client = AsyncOpenAI(api_key=api_key)

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> ChatResponse:
        """Send a chat completion request to OpenAI.

        Args:
            messages: List of chat messages
            model: Model to use (defaults to gpt-4o-mini)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)
            system_prompt: Optional system prompt to prepend

        Returns:
            ChatResponse with content and usage statistics
        """
        model = model or self.default_model
        model_config = get_model_config(model)

        # Prepare messages with optional system prompt
        prepared_messages = self._prepare_messages(messages, system_prompt)
        openai_messages = [
            {"role": m.role, "content": m.content} for m in prepared_messages
        ]

        try:
            response = await self.client.chat.completions.create(
                model=model_config.model_id,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            usage = response.usage
            return ChatResponse.from_tokens(
                content=response.choices[0].message.content or "",
                model=model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                model_config=model_config,
                finish_reason=response.choices[0].finish_reason or "stop",
            )

        except Exception as e:
            error_message = str(e)
            logger.error(
                "OpenAI chat error",
                model=model,
                error=error_message,
            )

            # Map OpenAI errors to our exceptions
            if "rate_limit" in error_message.lower():
                raise RateLimitError(
                    message=error_message,
                    vendor=self.vendor,
                    model=model,
                )
            elif "quota" in error_message.lower() or "insufficient" in error_message.lower():
                raise QuotaExceededError(
                    message=error_message,
                    vendor=self.vendor,
                    model=model,
                )
            elif "model" in error_message.lower() and "not found" in error_message.lower():
                raise ModelNotAvailableError(
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
        """Stream a chat completion response from OpenAI.

        Args:
            messages: List of chat messages
            model: Model to use (defaults to gpt-4o-mini)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)
            system_prompt: Optional system prompt to prepend

        Yields:
            String chunks of the response as they arrive
        """
        model = model or self.default_model
        model_config = get_model_config(model)

        # Check if model supports streaming
        if not model_config.supports_streaming:
            # Fall back to non-streaming for O1 models
            response = await self.chat(messages, model, max_tokens, temperature, system_prompt)
            yield response.content
            return

        # Prepare messages
        prepared_messages = self._prepare_messages(messages, system_prompt)
        openai_messages = [
            {"role": m.role, "content": m.content} for m in prepared_messages
        ]

        try:
            stream = await self.client.chat.completions.create(
                model=model_config.model_id,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            error_message = str(e)
            logger.error(
                "OpenAI stream error",
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
        """Generate embeddings using OpenAI.

        Args:
            texts: List of texts to embed
            model: Embedding model to use (defaults to text-embedding-3-small)

        Returns:
            EmbeddingResponse with embedding vectors
        """
        model = model or self.embedding_model

        try:
            response = await self.client.embeddings.create(
                model=model,
                input=texts,
            )

            embeddings = [item.embedding for item in response.data]
            total_tokens = response.usage.total_tokens if response.usage else 0

            # Calculate cost
            cost_per_1m = self.EMBEDDING_PRICING.get(model, 0.02)
            cost_usd = (total_tokens / 1_000_000) * cost_per_1m

            return EmbeddingResponse(
                embeddings=embeddings,
                model=model,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
            )

        except Exception as e:
            error_message = str(e)
            logger.error(
                "OpenAI embedding error",
                model=model,
                error=error_message,
            )
            raise AIProviderError(
                message=error_message,
                vendor=self.vendor,
                model=model,
            )
