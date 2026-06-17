"""Book club database models."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class BookClub(Base, UUIDMixin, TimestampMixin):
    """Book club entity."""

    __tablename__ = "book_clubs"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tagline: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    welcome_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="public", server_default="public")
    club_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    max_members: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    member_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_premium_only: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    featured_book_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    premium_features: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")

    members: Mapped[list["BookClubMember"]] = relationship("BookClubMember", back_populates="club", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<BookClub {self.name}>"


class BookClubMember(Base, UUIDMixin):
    """Book club membership."""

    __tablename__ = "book_club_members"

    book_club_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    custom_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rank_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    invited_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    invite_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now())

    club: Mapped["BookClub"] = relationship("BookClub", back_populates="members")

    __table_args__ = (
        UniqueConstraint("book_club_id", "user_id", name="uq_club_member"),
        Index("idx_club_members_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<BookClubMember club={self.book_club_id} user={self.user_id} role={self.role}>"


class BookClubBook(Base, UUIDMixin):
    """Books shared in a club."""

    __tablename__ = "book_club_books"

    book_club_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False)
    book_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    shared_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_exclusive: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    shared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now())

    __table_args__ = (UniqueConstraint("book_club_id", "book_id", name="uq_club_book"),)

    def __repr__(self) -> str:
        return f"<BookClubBook club={self.book_club_id} book={self.book_id}>"


class BookClubDiscussion(Base, UUIDMixin, TimestampMixin):
    """Discussion thread in a club."""

    __tablename__ = "book_club_discussions"

    club_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False, index=True)
    book_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="SET NULL"), nullable=True)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(50)), default=list, server_default="{}")
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    likes_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    replies_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    replies: Mapped[list["BookClubDiscussionReply"]] = relationship("BookClubDiscussionReply", back_populates="discussion", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<BookClubDiscussion {self.title[:30]}>"


class BookClubDiscussionReply(Base, UUIDMixin, TimestampMixin):
    """Reply to a discussion thread."""

    __tablename__ = "book_club_discussion_replies"

    discussion_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_club_discussions.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parent_reply_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("book_club_discussion_replies.id", ondelete="SET NULL"), nullable=True)
    likes_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    discussion: Mapped["BookClubDiscussion"] = relationship("BookClubDiscussion", back_populates="replies")

    def __repr__(self) -> str:
        return f"<BookClubDiscussionReply {self.id}>"


class BookClubInvite(Base, UUIDMixin, TimestampMixin):
    """Invite code for a club."""

    __tablename__ = "book_club_invites"

    club_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False)
    invite_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_uses: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invite_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<BookClubInvite {self.invite_code}>"


class BookClubActivity(Base, UUIDMixin):
    """Activity feed entry for a club."""

    __tablename__ = "book_club_activities"

    club_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    activity_data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    visibility: Mapped[str] = mapped_column(String(20), default="members", server_default="members")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now())

    def __repr__(self) -> str:
        return f"<BookClubActivity {self.activity_type}>"


class BookClubChallenge(Base, UUIDMixin, TimestampMixin):
    """Reading challenge in a club."""

    __tablename__ = "book_club_challenges"

    club_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    challenge_type: Mapped[str] = mapped_column(String(50), nullable=False, default="reading")
    target_value: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    target_unit: Mapped[str] = mapped_column(String(50), nullable=False, default="books")
    reward_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    participants: Mapped[list["BookClubChallengeParticipant"]] = relationship("BookClubChallengeParticipant", back_populates="challenge", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<BookClubChallenge {self.name}>"


class BookClubChallengeParticipant(Base, UUIDMixin):
    """Challenge participation."""

    __tablename__ = "book_club_challenge_participants"

    challenge_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_club_challenges.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_club_members.id", ondelete="CASCADE"), nullable=False)
    current_progress: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now())

    challenge: Mapped["BookClubChallenge"] = relationship("BookClubChallenge", back_populates="participants")

    def __repr__(self) -> str:
        return f"<BookClubChallengeParticipant challenge={self.challenge_id}>"


class BookClubNomination(Base, UUIDMixin, TimestampMixin):
    """Book nomination in a club."""

    __tablename__ = "book_club_nominations"

    club_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False, index=True)
    book_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    nominated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    nomination_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    nomination_month: Mapped[str | None] = mapped_column(String(7), nullable=True)
    votes_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")

    def __repr__(self) -> str:
        return f"<BookClubNomination club={self.club_id} book={self.book_id}>"


class BookClubVote(Base, UUIDMixin):
    """Vote on a nomination."""

    __tablename__ = "book_club_votes"

    nomination_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_club_nominations.id", ondelete="CASCADE"), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_club_members.id", ondelete="CASCADE"), nullable=False)
    vote_weight: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now())

    __table_args__ = (UniqueConstraint("nomination_id", "member_id", name="uq_nomination_vote"),)


class BookClubNotification(Base, UUIDMixin):
    """Notification for a club member."""

    __tablename__ = "book_club_notifications"

    club_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    data: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now())

    __table_args__ = (Index("idx_club_notifications_user_read", "user_id", "is_read"),)


class BookClubPosterHistory(Base, UUIDMixin):
    """Cover image version history."""

    __tablename__ = "book_club_poster_history"

    book_club_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False, index=True)
    cover_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_thumbnail_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    version_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now())


class BookClubExclusiveBook(Base, UUIDMixin):
    """Premium exclusive book access in a club."""

    __tablename__ = "book_club_exclusive_books"

    club_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False, index=True)
    book_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    added_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    access_level: Mapped[str] = mapped_column(String(20), default="members")
    minimum_points: Mapped[int] = mapped_column(Integer, default=0)
    minimum_rank: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now())


class BookClubMemberStats(Base, UUIDMixin, TimestampMixin):
    """Per-member statistics in a club."""

    __tablename__ = "book_club_member_stats"

    book_club_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_club_members.id", ondelete="CASCADE"), nullable=False)
    books_read: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    books_shared: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    discussions_started: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    comments_posted: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    events_attended: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_points: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    monthly_points: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    monthly_books_read: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reading_streak_days: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("book_club_id", "member_id", name="uq_club_member_stats"),)


class BookClubAchievement(Base, UUIDMixin, TimestampMixin):
    """Club-specific achievement definition."""

    __tablename__ = "book_club_achievements"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    points_value: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    requirements: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")


class BookClubMemberAchievement(Base, UUIDMixin):
    """Achievement earned by a club member."""

    __tablename__ = "book_club_member_achievements"

    achievement_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_club_achievements.id", ondelete="CASCADE"), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_club_members.id", ondelete="CASCADE"), nullable=False)
    club_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("book_clubs.id", ondelete="CASCADE"), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=func.now())

    __table_args__ = (UniqueConstraint("achievement_id", "member_id", name="uq_member_achievement"),)
