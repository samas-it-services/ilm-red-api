"""SQLAlchemy models package."""

from app.models.addon import (
    AddonErrorLog,
    AddonPermission,
    AddonRegistry,
    AddonReview,
    AddonStorage,
    AddonTab,
    AddonUsageAnalytics,
    BookClubAddonConfig,
    DefaultAddonSeed,
    GlobalAddonConfig,
)
from app.models.admin_settings import AdminSetting, MysticalMessage
from app.models.announcement import FeatureAnnouncement, FeatureAnnouncementView
from app.models.annotation import Bookmark, Highlight, Note
from app.models.audit import AuditLog, BookAuditLog
from app.models.base import Base
from app.models.billing import (
    AIBillingConfig,
    AIUsageRecord,
    BillingTransaction,
    MonthlyBillingSummary,
    UsageLimit,
    UserAIBilling,
    UserCredits,
)
from app.models.blog import (
    BlogCategory,
    BlogComment,
    BlogLike,
    BlogPost,
    BlogPostCategory,
    BlogPostTag,
    BlogTag,
    BlogView,
)
from app.models.book import (
    BOOK_CATEGORIES,
    Book,
    BookAIProcessing,
    BookPageGenerationJob,
    BookSummary,
    Favorite,
    Rating,
)
from app.models.book_extra import BookExtra
from app.models.book_club import (
    BookClub,
    BookClubAchievement,
    BookClubActivity,
    BookClubBook,
    BookClubChallenge,
    BookClubChallengeParticipant,
    BookClubDiscussion,
    BookClubDiscussionReply,
    BookClubExclusiveBook,
    BookClubInvite,
    BookClubMember,
    BookClubMemberAchievement,
    BookClubMemberStats,
    BookClubNomination,
    BookClubNotification,
    BookClubPosterHistory,
    BookClubVote,
)
from app.models.book_club_ai import (
    BookClubAIChatMessage,
    BookClubAIChatParticipant,
    BookClubAIChatSession,
    BookClubAICreditTransaction,
    BookClubAICredits,
    BookClubAIModel,
)
from app.models.chat import (
    ChatAdminAccessLog,
    ChatEncryptionKey,
    ChatMessage,
    ChatMessageRating,
    ChatSession,
    MessageFeedback,
)
from app.models.copyright import BookDiscoveryReward
from app.models.error_log import ErrorLog
from app.models.expert import ExpertConfiguration, SessionAnalytics, SessionParticipant
from app.models.gamification import (
    Badge,
    GamificationActivity,
    PointsHistory,
    Rank,
    UserActivityLog,
    UserBadge,
    UserRank,
)
from app.models.help import (
    HelpArticle,
    HelpArticleFeedback,
    HelpArticleScreenshot,
    HelpArticleShare,
    HelpArticleView,
    HelpCategory,
)
from app.models.issue import UserIssue, UserIssueResponse
from app.models.page import PageImage, TextChunk
from app.models.premium import (
    PremiumFeature,
    PremiumRequest,
    StripePaymentIntent,
    UserPremiumSubscription,
    UserUploadLimit,
)
from app.models.progress import ReadingProgress
from app.models.public_qa import (
    PublicQA,
    PublicQAEditHistory,
    PublicQAFeedback,
    PublicQAView,
    PublicQAVote,
)
from app.models.quote import Quote, QuoteView
from app.models.ranking import (
    ContextPointsHistory,
    RankingContext,
    RankingSetting,
    UserContextRanking,
)
from app.models.rating_flag import RatingFlag
from app.models.rbac import (
    Permission,
    Role,
    RoleAssignmentLog,
    RolePermission,
    UserRole,
)
from app.models.safety import SafetyFlag
from app.models.search_analytics import SearchAnalytics
from app.models.suggestion import (
    SuggestionConfig,
    SuggestionFeedback,
    SuggestionNotification,
    SuggestionSystemConfig,
    UserSuggestion,
    UserSuggestionUsage,
)
from app.models.user import ApiKey, OAuthAccount, RefreshToken, User

__all__ = [
    # Base
    "Base",
    # User & Auth
    "User",
    "OAuthAccount",
    "ApiKey",
    "RefreshToken",
    # RBAC
    "Role",
    "Permission",
    "RolePermission",
    "UserRole",
    "RoleAssignmentLog",
    # Admin Settings
    "AdminSetting",
    "MysticalMessage",
    # Audit
    "BookAuditLog",
    "AuditLog",
    # Books
    "Book",
    "BookAIProcessing",
    "BookSummary",
    "BookPageGenerationJob",
    "BookExtra",
    "Rating",
    "RatingFlag",
    "Favorite",
    "BOOK_CATEGORIES",
    # Annotations
    "Bookmark",
    "Highlight",
    "Note",
    # Book Clubs
    "BookClub",
    "BookClubMember",
    "BookClubBook",
    "BookClubDiscussion",
    "BookClubDiscussionReply",
    "BookClubInvite",
    "BookClubActivity",
    "BookClubChallenge",
    "BookClubChallengeParticipant",
    "BookClubNomination",
    "BookClubVote",
    "BookClubNotification",
    "BookClubPosterHistory",
    "BookClubExclusiveBook",
    "BookClubMemberStats",
    "BookClubAchievement",
    "BookClubMemberAchievement",
    # Book Club AI
    "BookClubAICredits",
    "BookClubAICreditTransaction",
    "BookClubAIModel",
    "BookClubAIChatSession",
    "BookClubAIChatMessage",
    "BookClubAIChatParticipant",
    # Chat
    "ChatSession",
    "ChatMessage",
    "ChatAdminAccessLog",
    "ChatEncryptionKey",
    "ChatMessageRating",
    "MessageFeedback",
    # Billing
    "UserCredits",
    "BillingTransaction",
    "UsageLimit",
    "AIBillingConfig",
    "UserAIBilling",
    "AIUsageRecord",
    "MonthlyBillingSummary",
    # Gamification
    "GamificationActivity",
    "PointsHistory",
    "UserActivityLog",
    "Badge",
    "UserBadge",
    "Rank",
    "UserRank",
    # Rankings
    "RankingContext",
    "RankingSetting",
    "UserContextRanking",
    "ContextPointsHistory",
    # Addons
    "AddonRegistry",
    "AddonPermission",
    "AddonTab",
    "AddonStorage",
    "AddonErrorLog",
    "AddonUsageAnalytics",
    "AddonReview",
    "GlobalAddonConfig",
    "BookClubAddonConfig",
    "DefaultAddonSeed",
    # Pages & Safety
    "SafetyFlag",
    "PageImage",
    "TextChunk",
    # Progress
    "ReadingProgress",
    # Error Logging
    "ErrorLog",
    # Premium
    "PremiumRequest",
    "PremiumFeature",
    "UserPremiumSubscription",
    "StripePaymentIntent",
    "UserUploadLimit",
    # Expert
    "ExpertConfiguration",
    "SessionParticipant",
    "SessionAnalytics",
    # Suggestion
    "UserSuggestion",
    "SuggestionConfig",
    "SuggestionSystemConfig",
    "SuggestionFeedback",
    "SuggestionNotification",
    "UserSuggestionUsage",
    # Copyright
    "BookDiscoveryReward",
    # Issues
    "UserIssue",
    "UserIssueResponse",
    # Quotes
    "Quote",
    "QuoteView",
    # Public QA
    "PublicQA",
    "PublicQAEditHistory",
    "PublicQAFeedback",
    "PublicQAView",
    "PublicQAVote",
    # Search Analytics
    "SearchAnalytics",
    # Blog
    "BlogPost",
    "BlogCategory",
    "BlogTag",
    "BlogPostCategory",
    "BlogPostTag",
    "BlogComment",
    "BlogLike",
    "BlogView",
    # Help/Documentation
    "HelpCategory",
    "HelpArticle",
    "HelpArticleView",
    "HelpArticleFeedback",
    "HelpArticleShare",
    "HelpArticleScreenshot",
    # Feature Announcements
    "FeatureAnnouncement",
    "FeatureAnnouncementView",
]
