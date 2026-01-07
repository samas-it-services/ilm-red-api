"""Qwen (Alibaba Cloud) provider implementation.

Uses the DashScope API for Qwen models.

Supports:
- Qwen-Turbo (fast, cost-effective)
- Qwen-Plus (balanced)
- Qwen-Max (most capable)
- Text embeddings

API Documentation: https://help.aliyun.com/zh/dashscope/
"""

from typing import AsyncIterator

import httpx
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


class QwenProvider(AIProvider):
    """Qwen (Alibaba DashScope) API provider."""

    vendor = "qwen"
    default_model = "qwen-turbo"
    embedding_model = "text-embedding-v2"

    # DashScope API endpoints
    BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
    CHAT_ENDPOINT = "/services/aigc/text-generation/generation"
    EMBEDDING_ENDPOINT = "/services/embeddings/text-embedding/text-embedding"

    # Embedding pricing per 1M tokens
    EMBEDDING_COST_PER_1M = 0.07

    def __init__(self, api_key: str):
        """Initialize Qwen provider.

        Args:
            api_key: Alibaba Cloud DashScope API key
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
        """Send a chat completion request to Qwen.

        Args:
            messages: List of chat messages
            model: Model to use (defaults to qwen-turbo)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)
            system_prompt: Optional system prompt to prepend

        Returns:
            ChatResponse with content and usage statistics
        """
        model = model or self.default_model
        model_config = get_model_config(model)

        # Prepare messages
        prepared_messages = self._prepare_messages(messages, system_prompt)
        qwen_messages = [
            {"role": m.role, "content": m.content} for m in prepared_messages
        ]

        # Build request payload
        payload = {
            "model": model_config.model_id,
            "input": {
                "messages": qwen_messages,
            },
            "parameters": {
                "max_tokens": max_tokens,
                "temperature": temperature,
                "result_format": "message",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}{self.CHAT_ENDPOINT}",
                    headers=self.headers,
                    json=payload,
                )

                if response.status_code != 200:
                    self._handle_error_response(response, model)

                data = response.json()

                # Extract response content and usage
                output = data.get("output", {})
                usage = data.get("usage", {})

                content = ""
                if "choices" in output:
                    content = output["choices"][0].get("message", {}).get("content", "")
                elif "text" in output:
                    content = output["text"]

                return ChatResponse.from_tokens(
                    content=content,
                    model=model,
                    prompt_tokens=usage.get("input_tokens", 0),
                    completion_tokens=usage.get("output_tokens", 0),
                    model_config=model_config,
                    finish_reason=output.get("finish_reason", "stop"),
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
                "Qwen chat error",
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
        """Stream a chat completion response from Qwen.

        Args:
            messages: List of chat messages
            model: Model to use (defaults to qwen-turbo)
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
        qwen_messages = [
            {"role": m.role, "content": m.content} for m in prepared_messages
        ]

        # Build request payload with streaming enabled
        payload = {
            "model": model_config.model_id,
            "input": {
                "messages": qwen_messages,
            },
            "parameters": {
                "max_tokens": max_tokens,
                "temperature": temperature,
                "result_format": "message",
                "incremental_output": True,
            },
        }

        headers = {
            **self.headers,
            "X-DashScope-SSE": "enable",
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.BASE_URL}{self.CHAT_ENDPOINT}",
                    headers=headers,
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
                                    output = data.get("output", {})
                                    if "choices" in output:
                                        content = output["choices"][0].get("message", {}).get("content", "")
                                        if content:
                                            yield content
                                    elif "text" in output:
                                        yield output["text"]
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
                "Qwen stream error",
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
        """Generate embeddings using Qwen.

        Args:
            texts: List of texts to embed
            model: Embedding model to use (defaults to text-embedding-v2)

        Returns:
            EmbeddingResponse with embedding vectors
        """
        model = model or self.embedding_model

        payload = {
            "model": model,
            "input": {
                "texts": texts,
            },
            "parameters": {
                "text_type": "query",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}{self.EMBEDDING_ENDPOINT}",
                    headers=self.headers,
                    json=payload,
                )

                if response.status_code != 200:
                    self._handle_error_response(response, model)

                data = response.json()
                output = data.get("output", {})
                usage = data.get("usage", {})

                embeddings = [item["embedding"] for item in output.get("embeddings", [])]
                total_tokens = usage.get("total_tokens", 0)

                # Calculate cost
                cost_usd = (total_tokens / 1_000_000) * self.EMBEDDING_COST_PER_1M

                return EmbeddingResponse(
                    embeddings=embeddings,
                    model=model,
                    total_tokens=total_tokens,
                    cost_usd=cost_usd,
                )

        except Exception as e:
            if isinstance(e, (AIProviderError, RateLimitError, QuotaExceededError)):
                raise
            logger.error(
                "Qwen embedding error",
                model=model,
                error=str(e),
            )
            raise AIProviderError(
                message=str(e),
                vendor=self.vendor,
                model=model,
            )

    def _handle_error_response(self, response: httpx.Response, model: str) -> None:
        """Handle error responses from Qwen API.

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
            error_code = error_data.get("code", "")
            error_message = error_data.get("message", response.text)
        except Exception:
            error_code = ""
            error_message = response.text

        logger.error(
            "Qwen API error",
            status_code=response.status_code,
            error_code=error_code,
            error_message=error_message,
            model=model,
        )

        if response.status_code == 429 or "rate" in error_code.lower():
            raise RateLimitError(
                message=error_message,
                vendor=self.vendor,
                model=model,
                status_code=response.status_code,
            )
        elif "quota" in error_code.lower() or "insufficient" in error_message.lower():
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
