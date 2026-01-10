"""Anthropic (Claude) provider implementation.

Supports:
- Claude 3 Haiku (fast, cost-effective)
- Claude 3.5 Sonnet (balanced)
- Claude 3 Opus (most capable)

API Documentation: https://docs.anthropic.com/
"""

from collections.abc import AsyncIterator

import structlog
from anthropic import AsyncAnthropic

from app.ai import get_model_config
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

logger = structlog.get_logger(__name__)


class AnthropicProvider(AIProvider):
    """Anthropic (Claude) API provider."""

    vendor = "anthropic"
    default_model = "claude-3-haiku"
    embedding_model = None  # Anthropic doesn't offer embeddings

    def __init__(self, api_key: str):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
        """
        self.client = AsyncAnthropic(api_key=api_key)

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> ChatResponse:
        """Send a chat completion request to Anthropic.

        Args:
            messages: List of chat messages
            model: Model to use (defaults to claude-3-haiku)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1 for Anthropic)
            system_prompt: Optional system prompt to prepend

        Returns:
            ChatResponse with content and usage statistics
        """
        model = model or self.default_model
        model_config = get_model_config(model)

        # Anthropic has a different message format:
        # - system prompt is separate from messages
        # - messages must alternate user/assistant
        system = system_prompt or ""
        anthropic_messages = []

        for msg in messages:
            if msg.role == "system":
                # Prepend to system prompt
                system = f"{system}\n\n{msg.content}" if system else msg.content
            else:
                anthropic_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        # Ensure temperature is in Anthropic's range (0-1)
        temperature = min(temperature, 1.0)

        try:
            response = await self.client.messages.create(
                model=model_config.model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else None,
                messages=anthropic_messages,
            )

            # Extract content from response
            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, "text"):
                        content += block.text

            return ChatResponse.from_tokens(
                content=content,
                model=model,
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                model_config=model_config,
                finish_reason=response.stop_reason or "end_turn",
            )

        except Exception as e:
            error_message = str(e)
            logger.error(
                "Anthropic chat error",
                model=model,
                error=error_message,
            )

            # Map Anthropic errors to our exceptions
            if "rate_limit" in error_message.lower():
                raise RateLimitError(
                    message=error_message,
                    vendor=self.vendor,
                    model=model,
                )
            elif "credit" in error_message.lower() or "billing" in error_message.lower():
                raise QuotaExceededError(
                    message=error_message,
                    vendor=self.vendor,
                    model=model,
                )
            elif "model" in error_message.lower():
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
        """Stream a chat completion response from Anthropic.

        Args:
            messages: List of chat messages
            model: Model to use (defaults to claude-3-haiku)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1 for Anthropic)
            system_prompt: Optional system prompt to prepend

        Yields:
            String chunks of the response as they arrive
        """
        model = model or self.default_model
        model_config = get_model_config(model)

        # Prepare messages (same as chat method)
        system = system_prompt or ""
        anthropic_messages = []

        for msg in messages:
            if msg.role == "system":
                system = f"{system}\n\n{msg.content}" if system else msg.content
            else:
                anthropic_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        temperature = min(temperature, 1.0)

        try:
            async with self.client.messages.stream(
                model=model_config.model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else None,
                messages=anthropic_messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            error_message = str(e)
            logger.error(
                "Anthropic stream error",
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
        """Anthropic doesn't offer embeddings API.

        Args:
            texts: List of texts to embed
            model: Embedding model (not applicable)

        Raises:
            ModelNotAvailableError: Always, as Anthropic doesn't support embeddings
        """
        raise ModelNotAvailableError(
            message="Anthropic does not support embeddings. Use OpenAI or another provider.",
            vendor=self.vendor,
            model=model,
        )
