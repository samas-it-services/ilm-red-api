"""Book club repository for database operations."""

import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.book_club import (
    BookClub,
    BookClubActivity,
    BookClubBook,
    BookClubChallenge,
    BookClubChallengeParticipant,
    BookClubDiscussion,
    BookClubDiscussionReply,
    BookClubInvite,
    BookClubMember,
    BookClubNomination,
    BookClubVote,
)


class BookClubRepository:
    """Repository for book club database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Club CRUD
    async def create(self, **kwargs) -> BookClub:
        club = BookClub(**kwargs)
        self.db.add(club)
        await self.db.flush()
        await self.db.refresh(club)
        return club

    async def get_by_id(self, club_id: uuid.UUID) -> BookClub | None:
        stmt = select(BookClub).where(BookClub.id == club_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_clubs(
        self, user_id: uuid.UUID | None = None, visibility: str | None = None,
        page: int = 1, limit: int = 20,
    ) -> tuple[list[BookClub], int]:
        stmt = select(BookClub)
        count_stmt = select(func.count()).select_from(BookClub)

        if visibility:
            stmt = stmt.where(BookClub.visibility == visibility)
            count_stmt = count_stmt.where(BookClub.visibility == visibility)
        elif user_id:
            # Show public clubs + clubs user is member of
            member_clubs = select(BookClubMember.book_club_id).where(BookClubMember.user_id == user_id)
            stmt = stmt.where((BookClub.visibility == "public") | (BookClub.id.in_(member_clubs)))
            count_stmt = count_stmt.where((BookClub.visibility == "public") | (BookClub.id.in_(member_clubs)))
        else:
            stmt = stmt.where(BookClub.visibility == "public")
            count_stmt = count_stmt.where(BookClub.visibility == "public")

        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = stmt.order_by(BookClub.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def update(self, club_id: uuid.UUID, **kwargs) -> BookClub:
        club = await self.get_by_id(club_id)
        if club:
            for key, value in kwargs.items():
                if hasattr(club, key) and value is not None:
                    setattr(club, key, value)
            await self.db.flush()
            await self.db.refresh(club)
        return club

    async def delete(self, club_id: uuid.UUID) -> None:
        club = await self.get_by_id(club_id)
        if club:
            await self.db.delete(club)
            await self.db.flush()

    # Members
    async def get_member(self, club_id: uuid.UUID, user_id: uuid.UUID) -> BookClubMember | None:
        stmt = select(BookClubMember).where(
            BookClubMember.book_club_id == club_id, BookClubMember.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_member(self, club_id: uuid.UUID, user_id: uuid.UUID, role: str = "member", **kwargs) -> BookClubMember:
        member = BookClubMember(book_club_id=club_id, user_id=user_id, role=role, **kwargs)
        self.db.add(member)
        await self.db.flush()
        await self.db.refresh(member)
        return member

    async def update_member(self, club_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> BookClubMember | None:
        member = await self.get_member(club_id, user_id)
        if member:
            for key, value in kwargs.items():
                if hasattr(member, key):
                    setattr(member, key, value)
            await self.db.flush()
            await self.db.refresh(member)
        return member

    async def remove_member(self, club_id: uuid.UUID, user_id: uuid.UUID) -> None:
        member = await self.get_member(club_id, user_id)
        if member:
            await self.db.delete(member)
            await self.db.flush()

    async def list_members(self, club_id: uuid.UUID, page: int = 1, limit: int = 20) -> tuple[list[BookClubMember], int]:
        count_stmt = select(func.count()).select_from(BookClubMember).where(BookClubMember.book_club_id == club_id)
        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = select(BookClubMember).where(BookClubMember.book_club_id == club_id).order_by(BookClubMember.joined_at).offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def count_members(self, club_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(BookClubMember).where(BookClubMember.book_club_id == club_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    # Books
    async def add_book(self, club_id: uuid.UUID, book_id: uuid.UUID, shared_by: uuid.UUID) -> BookClubBook:
        book = BookClubBook(book_club_id=club_id, book_id=book_id, shared_by=shared_by)
        self.db.add(book)
        await self.db.flush()
        return book

    async def list_books(self, club_id: uuid.UUID, page: int = 1, limit: int = 20) -> tuple[list[BookClubBook], int]:
        count_stmt = select(func.count()).select_from(BookClubBook).where(BookClubBook.book_club_id == club_id, BookClubBook.deleted_at.is_(None))
        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = select(BookClubBook).where(BookClubBook.book_club_id == club_id, BookClubBook.deleted_at.is_(None)).order_by(BookClubBook.shared_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def remove_book(self, club_id: uuid.UUID, book_id: uuid.UUID, deleted_by: uuid.UUID) -> None:
        from datetime import UTC, datetime
        stmt = select(BookClubBook).where(BookClubBook.book_club_id == club_id, BookClubBook.book_id == book_id)
        result = await self.db.execute(stmt)
        book = result.scalar_one_or_none()
        if book:
            book.deleted_at = datetime.now(UTC)
            book.deleted_by = deleted_by
            await self.db.flush()

    # Discussions
    async def create_discussion(self, **kwargs) -> BookClubDiscussion:
        discussion = BookClubDiscussion(**kwargs)
        self.db.add(discussion)
        await self.db.flush()
        await self.db.refresh(discussion)
        return discussion

    async def list_discussions(self, club_id: uuid.UUID, page: int = 1, limit: int = 20) -> tuple[list[BookClubDiscussion], int]:
        count_stmt = select(func.count()).select_from(BookClubDiscussion).where(BookClubDiscussion.club_id == club_id)
        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = select(BookClubDiscussion).where(BookClubDiscussion.club_id == club_id).order_by(BookClubDiscussion.is_pinned.desc(), BookClubDiscussion.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_discussion(self, discussion_id: uuid.UUID) -> BookClubDiscussion | None:
        stmt = select(BookClubDiscussion).options(selectinload(BookClubDiscussion.replies)).where(BookClubDiscussion.id == discussion_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_reply(self, **kwargs) -> BookClubDiscussionReply:
        reply = BookClubDiscussionReply(**kwargs)
        self.db.add(reply)
        await self.db.flush()
        await self.db.refresh(reply)
        # Increment reply count
        stmt = select(BookClubDiscussion).where(BookClubDiscussion.id == reply.discussion_id)
        result = await self.db.execute(stmt)
        discussion = result.scalar_one_or_none()
        if discussion:
            discussion.replies_count += 1
            await self.db.flush()
        return reply

    # Invites
    async def create_invite(self, club_id: uuid.UUID, created_by: uuid.UUID, **kwargs) -> BookClubInvite:
        code = secrets.token_urlsafe(8)
        invite = BookClubInvite(club_id=club_id, invite_code=code, created_by=created_by, **kwargs)
        self.db.add(invite)
        await self.db.flush()
        await self.db.refresh(invite)
        return invite

    async def get_invite_by_code(self, code: str) -> BookClubInvite | None:
        stmt = select(BookClubInvite).where(BookClubInvite.invite_code == code, BookClubInvite.is_active.is_(True))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_invites(self, club_id: uuid.UUID) -> list[BookClubInvite]:
        stmt = select(BookClubInvite).where(BookClubInvite.club_id == club_id).order_by(BookClubInvite.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def increment_invite_uses(self, invite_id: uuid.UUID) -> None:
        stmt = select(BookClubInvite).where(BookClubInvite.id == invite_id)
        result = await self.db.execute(stmt)
        invite = result.scalar_one_or_none()
        if invite:
            invite.current_uses += 1
            if invite.max_uses and invite.current_uses >= invite.max_uses:
                invite.is_active = False
            await self.db.flush()

    # Activities
    async def log_activity(self, club_id: uuid.UUID, user_id: uuid.UUID | None, activity_type: str, data: dict) -> BookClubActivity:
        activity = BookClubActivity(club_id=club_id, user_id=user_id, activity_type=activity_type, activity_data=data)
        self.db.add(activity)
        await self.db.flush()
        return activity

    async def list_activities(self, club_id: uuid.UUID, page: int = 1, limit: int = 20) -> tuple[list[BookClubActivity], int]:
        count_stmt = select(func.count()).select_from(BookClubActivity).where(BookClubActivity.club_id == club_id)
        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = select(BookClubActivity).where(BookClubActivity.club_id == club_id).order_by(BookClubActivity.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    # Challenges
    async def create_challenge(self, **kwargs) -> BookClubChallenge:
        challenge = BookClubChallenge(**kwargs)
        self.db.add(challenge)
        await self.db.flush()
        await self.db.refresh(challenge)
        return challenge

    async def list_challenges(self, club_id: uuid.UUID) -> list[BookClubChallenge]:
        stmt = select(BookClubChallenge).where(BookClubChallenge.club_id == club_id).order_by(BookClubChallenge.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def join_challenge(self, challenge_id: uuid.UUID, member_id: uuid.UUID) -> BookClubChallengeParticipant:
        participant = BookClubChallengeParticipant(challenge_id=challenge_id, member_id=member_id)
        self.db.add(participant)
        await self.db.flush()
        return participant

    # Nominations
    async def create_nomination(self, **kwargs) -> BookClubNomination:
        nomination = BookClubNomination(**kwargs)
        self.db.add(nomination)
        await self.db.flush()
        await self.db.refresh(nomination)
        return nomination

    async def vote_nomination(self, nomination_id: uuid.UUID, member_id: uuid.UUID) -> BookClubVote:
        vote = BookClubVote(nomination_id=nomination_id, member_id=member_id)
        self.db.add(vote)
        await self.db.flush()
        # Increment count
        stmt = select(BookClubNomination).where(BookClubNomination.id == nomination_id)
        result = await self.db.execute(stmt)
        nomination = result.scalar_one_or_none()
        if nomination:
            nomination.votes_count += 1
            await self.db.flush()
        return vote

    # Stats
    async def get_stats(self, club_id: uuid.UUID) -> dict:
        member_count = await self.count_members(club_id)
        book_count_stmt = select(func.count()).select_from(BookClubBook).where(BookClubBook.book_club_id == club_id, BookClubBook.deleted_at.is_(None))
        discussion_count_stmt = select(func.count()).select_from(BookClubDiscussion).where(BookClubDiscussion.club_id == club_id)
        challenge_count_stmt = select(func.count()).select_from(BookClubChallenge).where(BookClubChallenge.club_id == club_id, BookClubChallenge.is_active.is_(True))

        book_count = (await self.db.execute(book_count_stmt)).scalar() or 0
        discussion_count = (await self.db.execute(discussion_count_stmt)).scalar() or 0
        challenge_count = (await self.db.execute(challenge_count_stmt)).scalar() or 0

        return {
            "member_count": member_count,
            "book_count": book_count,
            "discussion_count": discussion_count,
            "active_challenges": challenge_count,
        }
