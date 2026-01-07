"""AI providers package.

This module provides a vendor-agnostic AI abstraction layer with support for multiple
AI providers (OpenAI, Qwen, Anthropic, Google, xAI, DeepSeek) and intelligent model
routing based on book visibility and user preferences.

Usage:
    from app.ai import get_ai_provider, get_model_config, MODEL_REGISTRY

    # Get a provider by vendor name
    provider = get_ai_provider("openai")
    response = await provider.chat(messages)

    # Get model configuration
    config = get_model_config("gpt-4o-mini")
    print(f"Cost: ${config.calculate_cost(1000, 500):.6f}")
"""

from app.ai.base import (
    AIProvider,
    AIProviderError,
    ChatMessage,
    ChatResponse,
    Citation,
    EmbeddingResponse,
    ModelConfig,
    ModelNotAvailableError,
    QuotaExceededError,
    RateLimitError,
)

# Model registry with pricing and capabilities (as of January 2025)
MODEL_REGISTRY: dict[str, ModelConfig] = {
    # ============= QWEN MODELS (Default for public books - cost-effective) =============
    "qwen-turbo": ModelConfig(
        vendor="qwen",
        model_id="qwen-turbo",
        display_name="Qwen Turbo",
        max_tokens=8192,
        input_cost_per_1m=0.10,
        output_cost_per_1m=0.30,
        context_window=8192,
    ),
    "qwen-plus": ModelConfig(
        vendor="qwen",
        model_id="qwen-plus",
        display_name="Qwen Plus",
        max_tokens=32768,
        input_cost_per_1m=0.40,
        output_cost_per_1m=1.20,
        context_window=131072,
    ),
    "qwen-max": ModelConfig(
        vendor="qwen",
        model_id="qwen-max",
        display_name="Qwen Max",
        max_tokens=32768,
        input_cost_per_1m=2.00,
        output_cost_per_1m=6.00,
        context_window=32768,
        supports_vision=True,
    ),
    "qwen-max-longcontext": ModelConfig(
        vendor="qwen",
        model_id="qwen-max-longcontext",
        display_name="Qwen Max Long Context",
        max_tokens=32768,
        input_cost_per_1m=2.00,
        output_cost_per_1m=6.00,
        context_window=1000000,
    ),
    # ============= OPENAI MODELS =============
    "gpt-4o-mini": ModelConfig(
        vendor="openai",
        model_id="gpt-4o-mini",
        display_name="GPT-4o Mini",
        max_tokens=16384,
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
        context_window=128000,
        supports_vision=True,
        supports_function_calling=True,
    ),
    "gpt-4o": ModelConfig(
        vendor="openai",
        model_id="gpt-4o",
        display_name="GPT-4o",
        max_tokens=16384,
        input_cost_per_1m=2.50,
        output_cost_per_1m=10.00,
        context_window=128000,
        supports_vision=True,
        supports_function_calling=True,
    ),
    "gpt-4-turbo": ModelConfig(
        vendor="openai",
        model_id="gpt-4-turbo",
        display_name="GPT-4 Turbo",
        max_tokens=4096,
        input_cost_per_1m=10.00,
        output_cost_per_1m=30.00,
        context_window=128000,
        supports_vision=True,
        supports_function_calling=True,
    ),
    "o1-mini": ModelConfig(
        vendor="openai",
        model_id="o1-mini",
        display_name="O1 Mini (Reasoning)",
        max_tokens=65536,
        input_cost_per_1m=3.00,
        output_cost_per_1m=12.00,
        context_window=128000,
        supports_streaming=False,  # O1 doesn't support streaming
    ),
    # ============= ANTHROPIC MODELS =============
    "claude-3-haiku": ModelConfig(
        vendor="anthropic",
        model_id="claude-3-haiku-20240307",
        display_name="Claude 3 Haiku",
        max_tokens=4096,
        input_cost_per_1m=0.25,
        output_cost_per_1m=1.25,
        context_window=200000,
        supports_vision=True,
    ),
    "claude-3-sonnet": ModelConfig(
        vendor="anthropic",
        model_id="claude-3-5-sonnet-20241022",
        display_name="Claude 3.5 Sonnet",
        max_tokens=8192,
        input_cost_per_1m=3.00,
        output_cost_per_1m=15.00,
        context_window=200000,
        supports_vision=True,
    ),
    "claude-3-opus": ModelConfig(
        vendor="anthropic",
        model_id="claude-3-opus-20240229",
        display_name="Claude 3 Opus",
        max_tokens=4096,
        input_cost_per_1m=15.00,
        output_cost_per_1m=75.00,
        context_window=200000,
        supports_vision=True,
    ),
    # ============= GOOGLE MODELS =============
    "gemini-1.5-flash": ModelConfig(
        vendor="google",
        model_id="gemini-1.5-flash",
        display_name="Gemini 1.5 Flash",
        max_tokens=8192,
        input_cost_per_1m=0.075,
        output_cost_per_1m=0.30,
        context_window=1000000,
        supports_vision=True,
    ),
    "gemini-1.5-pro": ModelConfig(
        vendor="google",
        model_id="gemini-1.5-pro",
        display_name="Gemini 1.5 Pro",
        max_tokens=8192,
        input_cost_per_1m=1.25,
        output_cost_per_1m=5.00,
        context_window=2000000,
        supports_vision=True,
    ),
    "gemini-2.0-flash": ModelConfig(
        vendor="google",
        model_id="gemini-2.0-flash-exp",
        display_name="Gemini 2.0 Flash",
        max_tokens=8192,
        input_cost_per_1m=0.10,
        output_cost_per_1m=0.40,
        context_window=1000000,
        supports_vision=True,
    ),
    # ============= XAI (GROK) MODELS =============
    "grok-beta": ModelConfig(
        vendor="xai",
        model_id="grok-beta",
        display_name="Grok Beta",
        max_tokens=131072,
        input_cost_per_1m=5.00,
        output_cost_per_1m=15.00,
        context_window=131072,
    ),
    "grok-2": ModelConfig(
        vendor="xai",
        model_id="grok-2-1212",
        display_name="Grok 2",
        max_tokens=131072,
        input_cost_per_1m=2.00,
        output_cost_per_1m=10.00,
        context_window=131072,
        supports_vision=True,
    ),
    # ============= DEEPSEEK MODELS =============
    "deepseek-chat": ModelConfig(
        vendor="deepseek",
        model_id="deepseek-chat",
        display_name="DeepSeek Chat",
        max_tokens=8192,
        input_cost_per_1m=0.14,
        output_cost_per_1m=0.28,
        context_window=64000,
    ),
    "deepseek-coder": ModelConfig(
        vendor="deepseek",
        model_id="deepseek-coder",
        display_name="DeepSeek Coder",
        max_tokens=8192,
        input_cost_per_1m=0.14,
        output_cost_per_1m=0.28,
        context_window=64000,
    ),
}

# Models available to free tier users
FREE_TIER_MODELS = {
    "qwen-turbo",  # Default for public books
    "gpt-4o-mini",
    "gemini-1.5-flash",
    "deepseek-chat",
    "claude-3-haiku",
}

# Default models by book visibility
DEFAULT_MODEL_PUBLIC = "qwen-turbo"  # Cost-effective for public books
DEFAULT_MODEL_PRIVATE = "gpt-4o-mini"  # Good balance for private books


def get_model_config(model_id: str) -> ModelConfig:
    """Get model configuration by model ID.

    Args:
        model_id: The model identifier (e.g., "gpt-4o-mini", "qwen-turbo")

    Returns:
        ModelConfig with pricing and capabilities

    Raises:
        ValueError: If model ID is not found in registry
    """
    if model_id not in MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model: {model_id}. "
            f"Available models: {', '.join(MODEL_REGISTRY.keys())}"
        )
    return MODEL_REGISTRY[model_id]


def get_models_by_vendor(vendor: str) -> list[ModelConfig]:
    """Get all models for a specific vendor.

    Args:
        vendor: Vendor name (e.g., "openai", "qwen")

    Returns:
        List of ModelConfig for the vendor
    """
    return [config for config in MODEL_REGISTRY.values() if config.vendor == vendor]


def get_ai_provider(vendor: str) -> AIProvider:
    """Factory function to get an AI provider instance.

    Args:
        vendor: Provider vendor name ("openai", "qwen", "anthropic", "google", "xai", "deepseek")

    Returns:
        AIProvider instance configured with API key from settings

    Raises:
        ValueError: If vendor is unknown or API key is not configured
    """
    from app.config import settings

    if vendor == "openai":
        from app.ai.providers.openai_provider import OpenAIProvider

        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured")
        return OpenAIProvider(api_key=settings.openai_api_key)

    elif vendor == "qwen":
        from app.ai.providers.qwen_provider import QwenProvider

        if not settings.qwen_api_key:
            raise ValueError("Qwen API key not configured")
        return QwenProvider(api_key=settings.qwen_api_key)

    elif vendor == "anthropic":
        from app.ai.providers.anthropic_provider import AnthropicProvider

        if not settings.anthropic_api_key:
            raise ValueError("Anthropic API key not configured")
        return AnthropicProvider(api_key=settings.anthropic_api_key)

    elif vendor == "google":
        from app.ai.providers.google_provider import GoogleProvider

        if not settings.google_api_key:
            raise ValueError("Google API key not configured")
        return GoogleProvider(api_key=settings.google_api_key)

    elif vendor == "xai":
        from app.ai.providers.xai_provider import XAIProvider

        if not settings.xai_api_key:
            raise ValueError("xAI API key not configured")
        return XAIProvider(api_key=settings.xai_api_key)

    elif vendor == "deepseek":
        from app.ai.providers.deepseek_provider import DeepSeekProvider

        if not settings.deepseek_api_key:
            raise ValueError("DeepSeek API key not configured")
        return DeepSeekProvider(api_key=settings.deepseek_api_key)

    else:
        raise ValueError(
            f"Unknown vendor: {vendor}. "
            f"Supported vendors: openai, qwen, anthropic, google, xai, deepseek"
        )


def get_provider_for_model(model_id: str) -> AIProvider:
    """Get the appropriate provider for a model.

    Args:
        model_id: Model identifier

    Returns:
        AIProvider instance for the model's vendor

    Raises:
        ValueError: If model is unknown or provider not configured
    """
    config = get_model_config(model_id)
    return get_ai_provider(config.vendor)


__all__ = [
    # Base classes
    "AIProvider",
    "ChatMessage",
    "ChatResponse",
    "Citation",
    "EmbeddingResponse",
    "ModelConfig",
    # Exceptions
    "AIProviderError",
    "RateLimitError",
    "QuotaExceededError",
    "ModelNotAvailableError",
    # Registry and factory
    "MODEL_REGISTRY",
    "FREE_TIER_MODELS",
    "DEFAULT_MODEL_PUBLIC",
    "DEFAULT_MODEL_PRIVATE",
    "get_model_config",
    "get_models_by_vendor",
    "get_ai_provider",
    "get_provider_for_model",
]
