"""AI provider abstraction layer.

This module defines the abstract base class for AI providers and common data structures
used across all AI vendor implementations.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    """AI model configuration with pricing and capabilities."""

    vendor: str  # "openai", "qwen", "anthropic", "google", "xai", "deepseek"
    model_id: str  # "qwen-turbo", "gpt-4o-mini", etc.
    display_name: str
    max_tokens: int
    input_cost_per_1m: float  # Cost per 1M input tokens in USD
    output_cost_per_1m: float  # Cost per 1M output tokens in USD
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_function_calling: bool = False
    context_window: int = 0  # Total context window size (0 = same as max_tokens)

    def __post_init__(self) -> None:
        """Set context_window to max_tokens if not specified."""
        if self.context_window == 0:
            self.context_window = self.max_tokens

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate the cost for a request in USD.

        Args:
            prompt_tokens: Number of input/prompt tokens
            completion_tokens: Number of output/completion tokens

        Returns:
            Total cost in USD
        """
        input_cost = (prompt_tokens / 1_000_000) * self.input_cost_per_1m
        output_cost = (completion_tokens / 1_000_000) * self.output_cost_per_1m
        return input_cost + output_cost


@dataclass
class ChatMessage:
    """A single message in a chat conversation."""

    role: str  # "system", "user", "assistant"
    content: str
    name: str | None = None  # Optional name for the message author


@dataclass
class Citation:
    """A citation reference from the source material."""

    page: int | None = None
    chapter: str | None = None
    excerpt: str | None = None
    source: str | None = None


@dataclass
class ChatResponse:
    """Response from an AI chat completion request."""

    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    finish_reason: str = "stop"
    citations: list[Citation] = field(default_factory=list)

    @classmethod
    def from_tokens(
        cls,
        content: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        model_config: ModelConfig,
        finish_reason: str = "stop",
        citations: list[Citation] | None = None,
    ) -> "ChatResponse":
        """Create a ChatResponse with automatic cost calculation.

        Args:
            content: Response content
            model: Model identifier
            prompt_tokens: Input token count
            completion_tokens: Output token count
            model_config: Model configuration with pricing
            finish_reason: Reason for completion
            citations: Optional list of citations

        Returns:
            ChatResponse with calculated cost
        """
        return cls(
            content=content,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            cost_usd=model_config.calculate_cost(prompt_tokens, completion_tokens),
            finish_reason=finish_reason,
            citations=citations or [],
        )


@dataclass
class EmbeddingResponse:
    """Response from an embedding request."""

    embeddings: list[list[float]]
    model: str
    total_tokens: int
    cost_usd: float


class AIProviderError(Exception):
    """Base exception for AI provider errors."""

    def __init__(
        self,
        message: str,
        vendor: str | None = None,
        model: str | None = None,
        status_code: int | None = None,
    ):
        self.vendor = vendor
        self.model = model
        self.status_code = status_code
        super().__init__(message)


class RateLimitError(AIProviderError):
    """Raised when rate limit is exceeded."""

    pass


class QuotaExceededError(AIProviderError):
    """Raised when quota/credits are exhausted."""

    pass


class ModelNotAvailableError(AIProviderError):
    """Raised when the requested model is not available."""

    pass


class AIProvider(ABC):
    """Abstract base class for AI providers.

    All AI vendor implementations must inherit from this class and implement
    the abstract methods for chat, streaming, and embeddings.
    """

    vendor: str  # Provider vendor name (e.g., "openai", "qwen")
    default_model: str  # Default model for this provider
    embedding_model: str | None = None  # Default embedding model

    @abstractmethod
    async def chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> ChatResponse:
        """Send a chat completion request.

        Args:
            messages: List of chat messages
            model: Model to use (defaults to provider's default)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)
            system_prompt: Optional system prompt to prepend

        Returns:
            ChatResponse with content and usage statistics

        Raises:
            AIProviderError: If the request fails
            RateLimitError: If rate limit is exceeded
            QuotaExceededError: If quota is exhausted
        """
        ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream a chat completion response.

        Args:
            messages: List of chat messages
            model: Model to use (defaults to provider's default)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)
            system_prompt: Optional system prompt to prepend

        Yields:
            String chunks of the response as they arrive

        Raises:
            AIProviderError: If the request fails
            RateLimitError: If rate limit is exceeded
        """
        ...

    @abstractmethod
    async def get_embeddings(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> EmbeddingResponse:
        """Generate embeddings for texts.

        Args:
            texts: List of texts to embed
            model: Embedding model to use (defaults to provider's default)

        Returns:
            EmbeddingResponse with embedding vectors

        Raises:
            AIProviderError: If the request fails
            ModelNotAvailableError: If embedding model not supported
        """
        ...

    def _prepare_messages(
        self,
        messages: list[ChatMessage],
        system_prompt: str | None = None,
    ) -> list[ChatMessage]:
        """Prepare messages by optionally prepending system prompt.

        Args:
            messages: Original message list
            system_prompt: Optional system prompt

        Returns:
            Message list with system prompt prepended if provided
        """
        if not system_prompt:
            return messages

        # Check if first message is already a system message
        if messages and messages[0].role == "system":
            # Prepend to existing system message
            messages = messages.copy()
            messages[0] = ChatMessage(
                role="system",
                content=f"{system_prompt}\n\n{messages[0].content}",
            )
            return messages

        # Add system message at the beginning
        return [ChatMessage(role="system", content=system_prompt)] + messages
