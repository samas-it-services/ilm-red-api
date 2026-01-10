"""Task classifier for intelligent model routing.

This module classifies user messages into task types to enable smart model selection.
Different task types benefit from different models - reasoning tasks need more capable
models while simple tasks can use cost-effective ones.
"""

import re
from enum import Enum
from dataclasses import dataclass


class TaskType(str, Enum):
    """Types of AI tasks for model routing."""

    SUMMARY = "summary"  # Summarization, key points extraction
    REASONING = "reasoning"  # Complex analysis, problem solving
    CREATIVE = "creative"  # Creative writing, stories, poetry
    CODE = "code"  # Code generation, debugging, explanation
    TRANSLATION = "translation"  # Language translation
    QA = "qa"  # Question answering, factual queries
    GENERAL = "general"  # General conversation, chat


@dataclass
class TaskClassification:
    """Result of task classification."""

    task_type: TaskType
    confidence: float  # 0.0 to 1.0
    keywords_matched: list[str]


# Keywords for each task type
TASK_KEYWORDS = {
    TaskType.SUMMARY: [
        "summarize", "summary", "summarise", "key points", "main points",
        "tldr", "tl;dr", "brief", "overview", "recap", "highlights",
        "condense", "shorten", "digest", "abstract", "gist",
    ],
    TaskType.REASONING: [
        "analyze", "analyse", "explain why", "reason", "reasoning",
        "compare", "contrast", "evaluate", "assess", "critique",
        "pros and cons", "advantages", "disadvantages", "implications",
        "cause and effect", "logic", "argument", "deduce", "infer",
        "think through", "step by step", "break down",
    ],
    TaskType.CREATIVE: [
        "write a story", "write a poem", "creative", "imagine",
        "fiction", "narrative", "compose", "create", "invent",
        "make up", "brainstorm", "ideas for", "suggest", "dream up",
        "write me", "help me write",
    ],
    TaskType.CODE: [
        "code", "program", "function", "class", "algorithm",
        "debug", "fix this code", "error", "bug", "syntax",
        "python", "javascript", "java", "typescript", "sql",
        "api", "implement", "refactor", "optimize code",
        "programming", "developer", "software",
    ],
    TaskType.TRANSLATION: [
        "translate", "translation", "in arabic", "in english",
        "in french", "in spanish", "in german", "in chinese",
        "in urdu", "convert to", "say in", "how do you say",
    ],
    TaskType.QA: [
        "what is", "what are", "who is", "who was", "when did",
        "where is", "where did", "why is", "why did", "how does",
        "how do", "how many", "how much", "define", "definition",
        "meaning of", "explain", "tell me about", "describe",
    ],
}


def classify_task(message: str) -> TaskClassification:
    """Classify a user message into a task type.

    Uses keyword matching to determine the most likely task type.
    Falls back to GENERAL if no strong signal is detected.

    Args:
        message: The user's message text

    Returns:
        TaskClassification with type, confidence, and matched keywords
    """
    message_lower = message.lower()

    # Track matches for each task type
    matches: dict[TaskType, list[str]] = {t: [] for t in TaskType}

    for task_type, keywords in TASK_KEYWORDS.items():
        for keyword in keywords:
            if keyword in message_lower:
                matches[task_type].append(keyword)

    # Find the task type with most matches
    best_type = TaskType.GENERAL
    max_matches = 0
    matched_keywords: list[str] = []

    for task_type, keywords in matches.items():
        if len(keywords) > max_matches:
            max_matches = len(keywords)
            best_type = task_type
            matched_keywords = keywords

    # Calculate confidence based on number of matches
    if max_matches == 0:
        confidence = 0.5  # Default for general
    elif max_matches == 1:
        confidence = 0.6
    elif max_matches == 2:
        confidence = 0.75
    else:
        confidence = min(0.95, 0.75 + (max_matches - 2) * 0.05)

    return TaskClassification(
        task_type=best_type,
        confidence=confidence,
        keywords_matched=matched_keywords,
    )


# Model recommendations by task type and tier
# Format: {TaskType: {"free": model_id, "premium": model_id}}
TASK_MODEL_RECOMMENDATIONS = {
    TaskType.SUMMARY: {
        "free": "qwen-turbo",  # Fast and cheap for summarization
        "premium": "gpt-4o-mini",
    },
    TaskType.REASONING: {
        "free": "gpt-4o-mini",  # Better reasoning
        "premium": "gpt-4o",  # Best reasoning
    },
    TaskType.CREATIVE: {
        "free": "claude-3-haiku",  # Good creative writing
        "premium": "claude-3-sonnet",  # Best creative
    },
    TaskType.CODE: {
        "free": "deepseek-coder",  # Specialized for code
        "premium": "gpt-4o",  # Best code generation
    },
    TaskType.TRANSLATION: {
        "free": "qwen-plus",  # Good multilingual
        "premium": "gpt-4o",
    },
    TaskType.QA: {
        "free": "gemini-1.5-flash",  # Fast Q&A
        "premium": "gpt-4o-mini",
    },
    TaskType.GENERAL: {
        "free": "qwen-turbo",  # Cost-effective default
        "premium": "gpt-4o-mini",
    },
}


def get_recommended_model(
    task_type: TaskType,
    is_premium: bool = False,
) -> str:
    """Get recommended model for a task type.

    Args:
        task_type: The classified task type
        is_premium: Whether user has premium access

    Returns:
        Recommended model ID
    """
    recommendations = TASK_MODEL_RECOMMENDATIONS.get(
        task_type,
        TASK_MODEL_RECOMMENDATIONS[TaskType.GENERAL],
    )

    tier = "premium" if is_premium else "free"
    return recommendations[tier]


def classify_and_recommend(
    message: str,
    is_premium: bool = False,
) -> tuple[TaskClassification, str]:
    """Classify a message and get model recommendation.

    Convenience function that combines classification and recommendation.

    Args:
        message: User message
        is_premium: Whether user has premium access

    Returns:
        Tuple of (classification, recommended_model_id)
    """
    classification = classify_task(message)
    model = get_recommended_model(classification.task_type, is_premium)
    return classification, model
