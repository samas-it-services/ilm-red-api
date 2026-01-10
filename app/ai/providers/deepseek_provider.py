"""DeepSeek provider implementation.

Supports:
- DeepSeek Chat (general purpose)
- DeepSeek Coder (code-focused)

DeepSeek uses an OpenAI-compatible API.

API Documentation: https://platform.deepseek.com/api-docs/
"""

from collections.abc import AsyncIterator

import httpx
import structlog

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


class DeepSeekProvider(AIProvider):
    """DeepSeek API provider."""

    vendor = "deepseek"
    default_model = "deepseek-chat"
    embedding_model = None  # DeepSeek doesn't offer embeddings via API

    BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self, api_key: str):
        """Initialize DeepSeek provider.

        Args:
            api_key: DeepSeek API key
        """
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> ChatResponse:
        """Send a chat completion request to DeepSeek.

        Args:
            messages: List of chat messages
            model: Model to use (defaults to deepseek-chat)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)
            system_prompt: Optional system prompt to prepend

        Returns:
            ChatResponse with content and usage statistics
        """
        model = model or self.default_model
        model_config = get_model_config(model)

        # Prepare messages (OpenAI-compatible format)
        prepared_messages = self._prepare_messages(messages, system_prompt)
        deepseek_messages = [
            {"role": m.role, "content": m.content} for m in prepared_messages
        ]

        payload = {
            "model": model_config.model_id,
            "messages": deepseek_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )

                if response.status_code != 200:
                    self._handle_error_response(response, model)

                data = response.json()

                # Extract response (OpenAI-compatible format)
                choice = data["choices"][0]
                usage = data.get("usage", {})

                return ChatResponse.from_tokens(
                    content=choice["message"]["content"],
                    model=model,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    model_config=model_config,
                    finish_reason=choice.get("finish_reason", "stop"),
                )

        except httpx.TimeoutException:
            raise AIProviderError(
                message="Request timed out",
                vendor=self.vendor,
                model=model,
            )
        except Exception as e:
            if isinstance(e, (AIProviderError, RateLimitError, QuotaExceededError)):
                raise
            logger.error(
                "DeepSeek chat error",
                model=model,
                error=str(e),
            )
            raise AIProviderError(
                message=str(e),
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
        """Stream a chat completion response from DeepSeek.

        Args:
            messages: List of chat messages
            model: Model to use (defaults to deepseek-chat)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)
            system_prompt: Optional system prompt to prepend

        Yields:
            String chunks of the response as they arrive
        """
        model = model or self.default_model
        model_config = get_model_config(model)

        # Prepare messages
        prepared_messages = self._prepare_messages(messages, system_prompt)
        deepseek_messages = [
            {"role": m.role, "content": m.content} for m in prepared_messages
        ]

        payload = {
            "model": model_config.model_id,
            "messages": deepseek_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.BASE_URL}/chat/completions",
                    headers=self.headers,
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        await response.aread()
                        self._handle_error_response(response, model)

                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if data_str and data_str != "[DONE]":
                                try:
                                    import json
                                    data = json.loads(data_str)
                                    delta = data["choices"][0].get("delta", {})
                                    if delta.get("content"):
                                        yield delta["content"]
                                except json.JSONDecodeError:
                                    continue

        except httpx.TimeoutException:
            raise AIProviderError(
                message="Stream timed out",
                vendor=self.vendor,
                model=model,
            )
        except Exception as e:
            if isinstance(e, (AIProviderError, RateLimitError, QuotaExceededError)):
                raise
            logger.error(
                "DeepSeek stream error",
                model=model,
                error=str(e),
            )
            raise AIProviderError(
                message=str(e),
                vendor=self.vendor,
                model=model,
            )

    async def get_embeddings(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> EmbeddingResponse:
        """DeepSeek doesn't offer embeddings API.

        Args:
            texts: List of texts to embed
            model: Embedding model (not applicable)

        Raises:
            ModelNotAvailableError: Always, as DeepSeek doesn't support embeddings
        """
        raise ModelNotAvailableError(
            message="DeepSeek does not support embeddings. Use OpenAI or another provider.",
            vendor=self.vendor,
            model=model,
        )

    def _handle_error_response(self, response: httpx.Response, model: str) -> None:
        """Handle error responses from DeepSeek API.

        Args:
            response: HTTP response object
            model: Model that was being used

        Raises:
            RateLimitError: If rate limited
            QuotaExceededError: If quota exceeded
            AIProviderError: For other errors
        """
        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", response.text)
        except Exception:
            error_message = response.text

        logger.error(
            "DeepSeek API error",
            status_code=response.status_code,
            error_message=error_message,
            model=model,
        )

        if response.status_code == 429:
            raise RateLimitError(
                message=error_message,
                vendor=self.vendor,
                model=model,
                status_code=response.status_code,
            )
        elif response.status_code == 402 or "balance" in error_message.lower():
            raise QuotaExceededError(
                message=error_message,
                vendor=self.vendor,
                model=model,
                status_code=response.status_code,
            )
        else:
            raise AIProviderError(
                message=error_message,
                vendor=self.vendor,
                model=model,
                status_code=response.status_code,
            )
