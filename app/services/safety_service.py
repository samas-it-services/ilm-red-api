"""Safety service for content moderation.

This service checks user input and AI output for harmful content using
the OpenAI Moderation API and custom rules.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.safety import SafetyFlag

logger = structlog.get_logger(__name__)


class Severity(str, Enum):
    """Content violation severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Action(str, Enum):
    """Actions taken on flagged content."""

    ALLOWED = "allowed"
    WARNED = "warned"
    BLOCKED = "blocked"
    FLAGGED_FOR_REVIEW = "flagged_for_review"


@dataclass
class ModerationResult:
    """Result of content moderation check."""

    is_flagged: bool
    categories: dict[str, bool]
    scores: dict[str, float]
    severity: Severity
    action: Action
    flagged_categories: list[str]


# OpenAI Moderation categories
MODERATION_CATEGORIES = [
    "sexual",
    "hate",
    "harassment",
    "self-harm",
    "sexual/minors",
    "hate/threatening",
    "violence/graphic",
    "self-harm/intent",
    "self-harm/instructions",
    "harassment/threatening",
    "violence",
]

# Severity thresholds for category scores
SEVERITY_THRESHOLDS = {
    Severity.LOW: 0.3,
    Severity.MEDIUM: 0.5,
    Severity.HIGH: 0.7,
    Severity.CRITICAL: 0.9,
}

# Categories that should always block
ALWAYS_BLOCK_CATEGORIES = [
    "sexual/minors",
    "self-harm/instructions",
    "violence/graphic",
]


class SafetyService:
    """Service for content safety and moderation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_input(
        self,
        content: str,
        user_id: uuid.UUID,
        session_id: uuid.UUID | None = None,
    ) -> ModerationResult:
        """Check user input for harmful content.

        Args:
            content: User's input text
            user_id: User ID
            session_id: Optional chat session ID

        Returns:
            ModerationResult with check results
        """
        result = await self._moderate_content(content)

        # Log if flagged
        if result.is_flagged:
            await self._log_flag(
                user_id=user_id,
                content_type="input",
                content=content,
                result=result,
                session_id=session_id,
            )

            logger.warning(
                "input_flagged",
                user_id=str(user_id),
                severity=result.severity.value,
                action=result.action.value,
                categories=result.flagged_categories,
            )

        return result

    async def check_output(
        self,
        content: str,
        user_id: uuid.UUID,
        message_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
    ) -> ModerationResult:
        """Check AI output for harmful content.

        Args:
            content: AI's response text
            user_id: User ID
            message_id: Optional message ID
            session_id: Optional chat session ID

        Returns:
            ModerationResult with check results
        """
        result = await self._moderate_content(content)

        # Log if flagged
        if result.is_flagged:
            await self._log_flag(
                user_id=user_id,
                content_type="output",
                content=content,
                result=result,
                message_id=message_id,
                session_id=session_id,
            )

            logger.warning(
                "output_flagged",
                user_id=str(user_id),
                message_id=str(message_id) if message_id else None,
                severity=result.severity.value,
                action=result.action.value,
                categories=result.flagged_categories,
            )

        return result

    async def _moderate_content(self, content: str) -> ModerationResult:
        """Run content through moderation API.

        Args:
            content: Text to moderate

        Returns:
            ModerationResult
        """
        try:
            # Use OpenAI Moderation API
            import openai

            client = openai.AsyncOpenAI(api_key=settings.openai_api_key)

            response = await client.moderations.create(
                input=content,
                model="text-moderation-latest",
            )

            result = response.results[0]

            # Extract categories and scores
            categories = {}
            scores = {}
            flagged_categories = []

            for category in MODERATION_CATEGORIES:
                # Handle nested categories like "sexual/minors"
                category_key = category.replace("/", "_")
                is_flagged = getattr(result.categories, category_key, False)
                score = getattr(result.category_scores, category_key, 0.0)

                categories[category] = is_flagged
                scores[category] = score

                if is_flagged:
                    flagged_categories.append(category)

            # Determine severity based on highest score
            max_score = max(scores.values()) if scores else 0.0
            severity = self._score_to_severity(max_score)

            # Determine action
            action = self._determine_action(
                flagged_categories=flagged_categories,
                severity=severity,
                is_flagged=result.flagged,
            )

            return ModerationResult(
                is_flagged=result.flagged,
                categories=categories,
                scores=scores,
                severity=severity,
                action=action,
                flagged_categories=flagged_categories,
            )

        except Exception as e:
            logger.error("moderation_api_error", error=str(e))
            # Return safe default - don't block on API errors
            return ModerationResult(
                is_flagged=False,
                categories={},
                scores={},
                severity=Severity.LOW,
                action=Action.ALLOWED,
                flagged_categories=[],
            )

    def _score_to_severity(self, score: float) -> Severity:
        """Convert moderation score to severity level.

        Args:
            score: Highest category score

        Returns:
            Severity level
        """
        if score >= SEVERITY_THRESHOLDS[Severity.CRITICAL]:
            return Severity.CRITICAL
        elif score >= SEVERITY_THRESHOLDS[Severity.HIGH]:
            return Severity.HIGH
        elif score >= SEVERITY_THRESHOLDS[Severity.MEDIUM]:
            return Severity.MEDIUM
        else:
            return Severity.LOW

    def _determine_action(
        self,
        flagged_categories: list[str],
        severity: Severity,
        is_flagged: bool,
    ) -> Action:
        """Determine action to take based on moderation results.

        Args:
            flagged_categories: List of flagged category names
            severity: Severity level
            is_flagged: Whether content was flagged overall

        Returns:
            Action to take
        """
        if not is_flagged:
            return Action.ALLOWED

        # Check for always-block categories
        for category in flagged_categories:
            if category in ALWAYS_BLOCK_CATEGORIES:
                return Action.BLOCKED

        # Action based on severity
        if severity == Severity.CRITICAL:
            return Action.BLOCKED
        elif severity == Severity.HIGH:
            return Action.FLAGGED_FOR_REVIEW
        elif severity == Severity.MEDIUM:
            return Action.WARNED
        else:
            return Action.ALLOWED

    async def _log_flag(
        self,
        user_id: uuid.UUID,
        content_type: Literal["input", "output"],
        content: str,
        result: ModerationResult,
        message_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
    ) -> SafetyFlag:
        """Log a safety flag to the database.

        Args:
            user_id: User ID
            content_type: 'input' or 'output'
            content: Original content
            result: Moderation result
            message_id: Optional message ID
            session_id: Optional session ID

        Returns:
            Created SafetyFlag record
        """
        flag = SafetyFlag(
            user_id=user_id,
            message_id=message_id,
            session_id=session_id,
            content_type=content_type,
            content_preview=content[:500] if content else None,
            categories=result.categories,
            severity=result.severity.value,
            scores=result.scores,
            action_taken=result.action.value,
            model_used="text-moderation-latest",
        )

        self.db.add(flag)
        await self.db.flush()
        await self.db.refresh(flag)
        return flag

    async def get_user_flags(
        self,
        user_id: uuid.UUID,
        severity: Severity | None = None,
        limit: int = 100,
    ) -> list[SafetyFlag]:
        """Get safety flags for a user.

        Args:
            user_id: User ID
            severity: Optional filter by severity
            limit: Maximum flags to return

        Returns:
            List of SafetyFlag records
        """
        conditions = [SafetyFlag.user_id == user_id]

        if severity:
            conditions.append(SafetyFlag.severity == severity.value)

        stmt = (
            select(SafetyFlag)
            .where(and_(*conditions))
            .order_by(SafetyFlag.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_flags_for_review(
        self,
        limit: int = 50,
    ) -> list[SafetyFlag]:
        """Get flags that need manual review.

        Args:
            limit: Maximum flags to return

        Returns:
            List of SafetyFlag records needing review
        """
        stmt = (
            select(SafetyFlag)
            .where(SafetyFlag.action_taken == Action.FLAGGED_FOR_REVIEW.value)
            .order_by(SafetyFlag.created_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_violation_count(
        self,
        user_id: uuid.UUID,
        days: int = 30,
    ) -> dict:
        """Get violation counts for a user over a time period.

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            Dictionary with violation counts by severity
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        stmt = (
            select(
                SafetyFlag.severity,
                func.count(SafetyFlag.id),
            )
            .where(
                and_(
                    SafetyFlag.user_id == user_id,
                    SafetyFlag.created_at >= cutoff,
                )
            )
            .group_by(SafetyFlag.severity)
        )

        result = await self.db.execute(stmt)
        counts = {row[0]: row[1] for row in result.all()}

        return {
            "low": counts.get("low", 0),
            "medium": counts.get("medium", 0),
            "high": counts.get("high", 0),
            "critical": counts.get("critical", 0),
            "total": sum(counts.values()),
            "period_days": days,
        }

    def should_block_user(
        self,
        violation_counts: dict,
    ) -> bool:
        """Check if a user should be temporarily blocked based on violations.

        Args:
            violation_counts: Dictionary from get_user_violation_count

        Returns:
            True if user should be blocked
        """
        # Block if:
        # - Any critical violation
        # - 3+ high violations in period
        # - 10+ medium violations in period
        if violation_counts.get("critical", 0) > 0:
            return True
        if violation_counts.get("high", 0) >= 3:
            return True
        if violation_counts.get("medium", 0) >= 10:
            return True
        return False


# Import at module level
from datetime import timedelta
