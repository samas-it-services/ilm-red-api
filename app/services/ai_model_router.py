"""AI Model Router Service.

This service handles intelligent model selection based on:
1. Book visibility (public vs private)
2. User preferences
3. Tier access (free vs premium)

Model Routing Rules:
- Public books: Use Qwen (cost-effective) by default
- Private books: Use user's preferred model, or GPT-4o-mini if not set
- User can always override by specifying model explicitly
"""

from uuid import UUID

import structlog

from app.ai import (
    DEFAULT_MODEL_PRIVATE,
    DEFAULT_MODEL_PUBLIC,
    FREE_TIER_MODELS,
    MODEL_REGISTRY,
    AIProvider,
    ModelConfig,
    get_ai_provider,
    get_model_config,
)
from app.models.book import Book
from app.models.user import User

logger = structlog.get_logger(__name__)


class AIModelRouter:
    """Service for intelligent AI model routing."""

    @staticmethod
    def resolve_model(
        book: Book | None = None,
        user: User | None = None,
        requested_model: str | None = None,
    ) -> str:
        """Resolve which AI model to use based on context.

        Model selection priority:
        1. User's explicit request (if valid and accessible)
        2. User's default preference (for private books only)
        3. System default based on book visibility

        Args:
            book: The book being queried (None for general AI)
            user: The authenticated user (None for anonymous)
            requested_model: Explicitly requested model ID

        Returns:
            Model ID to use

        Raises:
            ValueError: If requested model is invalid or user doesn't have access
        """
        # If user explicitly requested a model, validate it
        if requested_model:
            if requested_model not in MODEL_REGISTRY:
                available = ", ".join(MODEL_REGISTRY.keys())
                raise ValueError(
                    f"Invalid model: {requested_model}. Available models: {available}"
                )

            # Check if user has access to this model
            if not AIModelRouter._user_can_access_model(user, requested_model):
                raise ValueError(
                    f"Model {requested_model} requires a premium subscription"
                )

            logger.debug(
                "Using explicitly requested model",
                model=requested_model,
                user_id=str(user.id) if user else None,
            )
            return requested_model

        # For private books, use user's preferred model
        if book and book.visibility == "private" and user:
            user_prefs = user.preferences or {}
            ai_prefs = user_prefs.get("ai", {})
            preferred_model = ai_prefs.get("default_model")

            if preferred_model and preferred_model in MODEL_REGISTRY:
                # Check if user can access their preferred model
                if AIModelRouter._user_can_access_model(user, preferred_model):
                    logger.debug(
                        "Using user's preferred model for private book",
                        model=preferred_model,
                        book_id=str(book.id),
                        user_id=str(user.id),
                    )
                    return preferred_model

            # Fall back to private book default
            logger.debug(
                "Using default model for private book",
                model=DEFAULT_MODEL_PRIVATE,
                book_id=str(book.id),
                user_id=str(user.id),
            )
            return DEFAULT_MODEL_PRIVATE

        # For public books or no book context, use cost-effective default
        logger.debug(
            "Using default model for public/no book context",
            model=DEFAULT_MODEL_PUBLIC,
            book_id=str(book.id) if book else None,
        )
        return DEFAULT_MODEL_PUBLIC

    @staticmethod
    def _user_can_access_model(user: User | None, model_id: str) -> bool:
        """Check if a user can access a specific model.

        Free tier users can only access FREE_TIER_MODELS.
        Premium users can access all models.

        Args:
            user: The user (None for anonymous)
            model_id: The model to check

        Returns:
            True if user can access the model
        """
        # Free tier models are accessible to everyone
        if model_id in FREE_TIER_MODELS:
            return True

        # Premium models require premium subscription
        if user and "premium" in (user.roles or []):
            return True

        return False

    @staticmethod
    def get_available_models(user: User | None = None) -> list[dict]:
        """Get list of models available to a user.

        Args:
            user: The user (None for anonymous)

        Returns:
            List of model info dictionaries
        """
        is_premium = user and "premium" in (user.roles or [])
        available = []

        for model_id, config in MODEL_REGISTRY.items():
            is_free_model = model_id in FREE_TIER_MODELS

            # Include model if user is premium or it's a free model
            if is_premium or is_free_model:
                available.append({
                    "id": model_id,
                    "name": config.display_name,
                    "vendor": config.vendor,
                    "maxTokens": config.max_tokens,
                    "contextWindow": config.context_window,
                    "inputCostPer1M": config.input_cost_per_1m,
                    "outputCostPer1M": config.output_cost_per_1m,
                    "supportsStreaming": config.supports_streaming,
                    "supportsVision": config.supports_vision,
                    "premium": not is_free_model,
                    "accessible": True,
                })
            else:
                # Show premium models as locked for free users
                available.append({
                    "id": model_id,
                    "name": config.display_name,
                    "vendor": config.vendor,
                    "maxTokens": config.max_tokens,
                    "contextWindow": config.context_window,
                    "inputCostPer1M": config.input_cost_per_1m,
                    "outputCostPer1M": config.output_cost_per_1m,
                    "supportsStreaming": config.supports_streaming,
                    "supportsVision": config.supports_vision,
                    "premium": True,
                    "accessible": False,
                })

        # Sort by vendor, then by cost
        available.sort(key=lambda x: (x["vendor"], x["inputCostPer1M"]))

        return available

    @staticmethod
    def get_models_by_vendor(
        vendor: str,
        user: User | None = None,
    ) -> list[dict]:
        """Get models for a specific vendor.

        Args:
            vendor: Vendor name (openai, qwen, etc.)
            user: The user (None for anonymous)

        Returns:
            List of model info dictionaries for the vendor
        """
        all_models = AIModelRouter.get_available_models(user)
        return [m for m in all_models if m["vendor"] == vendor]

    @staticmethod
    def get_provider_for_model(model_id: str) -> AIProvider:
        """Get the appropriate provider instance for a model.

        Args:
            model_id: Model identifier

        Returns:
            AIProvider instance for the model's vendor

        Raises:
            ValueError: If model is unknown or provider not configured
        """
        config = get_model_config(model_id)
        return get_ai_provider(config.vendor)

    @staticmethod
    def estimate_cost(
        model_id: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Estimate the cost for a request.

        Args:
            model_id: Model identifier
            prompt_tokens: Estimated input tokens
            completion_tokens: Estimated output tokens

        Returns:
            Estimated cost in USD
        """
        config = get_model_config(model_id)
        return config.calculate_cost(prompt_tokens, completion_tokens)

    @staticmethod
    def get_cheapest_model(
        user: User | None = None,
        min_context_window: int = 0,
        require_streaming: bool = False,
        require_vision: bool = False,
    ) -> str:
        """Get the cheapest model that meets requirements.

        Args:
            user: The user (to check access)
            min_context_window: Minimum context window required
            require_streaming: Whether streaming is required
            require_vision: Whether vision support is required

        Returns:
            Model ID of the cheapest suitable model
        """
        candidates = []

        for model_id, config in MODEL_REGISTRY.items():
            # Check access
            if not AIModelRouter._user_can_access_model(user, model_id):
                continue

            # Check requirements
            if config.context_window < min_context_window:
                continue
            if require_streaming and not config.supports_streaming:
                continue
            if require_vision and not config.supports_vision:
                continue

            # Calculate average cost per 1M tokens
            avg_cost = (config.input_cost_per_1m + config.output_cost_per_1m) / 2
            candidates.append((model_id, avg_cost))

        if not candidates:
            # Fall back to default public model
            return DEFAULT_MODEL_PUBLIC

        # Return cheapest
        candidates.sort(key=lambda x: x[1])
        return candidates[0][0]


# Convenience function for direct use
def resolve_model(
    book: Book | None = None,
    user: User | None = None,
    requested_model: str | None = None,
) -> str:
    """Resolve which AI model to use (convenience function).

    See AIModelRouter.resolve_model for full documentation.
    """
    return AIModelRouter.resolve_model(book, user, requested_model)


def get_available_models(user: User | None = None) -> list[dict]:
    """Get available models (convenience function).

    See AIModelRouter.get_available_models for full documentation.
    """
    return AIModelRouter.get_available_models(user)
