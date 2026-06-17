"""Book club service for business logic."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.book_club_repo import BookClubRepository
from app.schemas.book_club import (
    BookClubActivityResponse,
    BookClubChallengeResponse,
    BookClubDiscussionResponse,
    BookClubInviteResponse,
    BookClubMemberResponse,
    BookClubResponse,
    BookClubStatsResponse,
    DiscussionReplyResponse,
    NominationResponse,
)


class BookClubService:
    """Service for book club operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BookClubRepository(db)

    async def create_club(self, data, owner: User) -> BookClubResponse:
        club = await self.repo.create(owner_id=owner.id, **data.model_dump())
        await self.repo.add_member(club.id, owner.id, role="owner")
        await self.repo.log_activity(club.id, owner.id, "club_created", {"name": club.name})
        member_count = await self.repo.count_members(club.id)
        resp = BookClubResponse.model_validate(club)
        resp.member_count = member_count
        return resp

    async def list_clubs(self, user_id: uuid.UUID | None, page: int, limit: int, visibility: str | None = None):
        clubs, total = await self.repo.list_clubs(user_id, visibility, page, limit)
        results = []
        for club in clubs:
            resp = BookClubResponse.model_validate(club)
            resp.member_count = await self.repo.count_members(club.id)
            results.append(resp)
        return results, total

    async def get_club(self, club_id: uuid.UUID, user: User | None = None) -> BookClubResponse:
        club = await self.repo.get_by_id(club_id)
        if not club:
            raise HTTPException(status_code=404, detail="Book club not found")
        if club.visibility != "public" and user:
            member = await self.repo.get_member(club_id, user.id)
            if not member and not user.is_admin:
                raise HTTPException(status_code=403, detail="Not a member of this private club")
        elif club.visibility != "public":
            raise HTTPException(status_code=403, detail="Authentication required for private clubs")
        resp = BookClubResponse.model_validate(club)
        resp.member_count = await self.repo.count_members(club.id)
        return resp

    async def update_club(self, club_id: uuid.UUID, data, user: User) -> BookClubResponse:
        club = await self._check_club_admin(club_id, user)
        updated = await self.repo.update(club_id, **data.model_dump(exclude_unset=True))
        resp = BookClubResponse.model_validate(updated)
        resp.member_count = await self.repo.count_members(club_id)
        return resp

    async def delete_club(self, club_id: uuid.UUID, user: User) -> None:
        club = await self.repo.get_by_id(club_id)
        if not club:
            raise HTTPException(status_code=404, detail="Book club not found")
        if club.owner_id != user.id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Only the owner can delete the club")
        await self.repo.delete(club_id)

    async def add_member(self, club_id: uuid.UUID, user: User) -> BookClubMemberResponse:
        club = await self.repo.get_by_id(club_id)
        if not club:
            raise HTTPException(status_code=404, detail="Book club not found")
        if club.visibility != "public":
            raise HTTPException(status_code=403, detail="Cannot join a private club without invite")
        existing = await self.repo.get_member(club_id, user.id)
        if existing:
            raise HTTPException(status_code=409, detail="Already a member")
        count = await self.repo.count_members(club_id)
        if count >= club.max_members:
            raise HTTPException(status_code=400, detail="Club is full")
        member = await self.repo.add_member(club_id, user.id)
        await self.repo.log_activity(club_id, user.id, "member_joined", {"user_id": str(user.id)})
        return BookClubMemberResponse.model_validate(member)

    async def update_member_role(self, club_id: uuid.UUID, target_user_id: uuid.UUID, role: str, requester: User) -> BookClubMemberResponse:
        await self._check_club_admin(club_id, requester)
        member = await self.repo.update_member(club_id, target_user_id, role=role)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        return BookClubMemberResponse.model_validate(member)

    async def remove_member(self, club_id: uuid.UUID, target_user_id: uuid.UUID, requester: User) -> None:
        club = await self.repo.get_by_id(club_id)
        if not club:
            raise HTTPException(status_code=404, detail="Book club not found")
        if club.owner_id == target_user_id:
            raise HTTPException(status_code=400, detail="Cannot remove the club owner")
        if target_user_id != requester.id:
            await self._check_club_admin(club_id, requester)
        await self.repo.remove_member(club_id, target_user_id)

    async def list_members(self, club_id: uuid.UUID, page: int, limit: int):
        members, total = await self.repo.list_members(club_id, page, limit)
        return [BookClubMemberResponse.model_validate(m) for m in members], total

    # Books
    async def add_book(self, club_id: uuid.UUID, book_id: uuid.UUID, user: User):
        await self._check_membership(club_id, user)
        await self.repo.add_book(club_id, book_id, user.id)
        await self.repo.log_activity(club_id, user.id, "book_added", {"book_id": str(book_id)})

    async def list_books(self, club_id: uuid.UUID, page: int, limit: int):
        return await self.repo.list_books(club_id, page, limit)

    async def remove_book(self, club_id: uuid.UUID, book_id: uuid.UUID, user: User):
        await self._check_club_admin(club_id, user)
        await self.repo.remove_book(club_id, book_id, user.id)

    # Discussions
    async def create_discussion(self, club_id: uuid.UUID, data, user: User) -> BookClubDiscussionResponse:
        await self._check_membership(club_id, user)
        discussion = await self.repo.create_discussion(
            club_id=club_id, author_id=user.id,
            title=data.title, content=data.content,
            book_id=data.book_id, tags=data.tags,
        )
        await self.repo.log_activity(club_id, user.id, "discussion_created", {"title": data.title})
        return BookClubDiscussionResponse.model_validate(discussion)

    async def list_discussions(self, club_id: uuid.UUID, page: int, limit: int):
        discussions, total = await self.repo.list_discussions(club_id, page, limit)
        return [BookClubDiscussionResponse.model_validate(d) for d in discussions], total

    async def get_discussion(self, club_id: uuid.UUID, discussion_id: uuid.UUID):
        discussion = await self.repo.get_discussion(discussion_id)
        if not discussion or discussion.club_id != club_id:
            raise HTTPException(status_code=404, detail="Discussion not found")
        return BookClubDiscussionResponse.model_validate(discussion)

    async def create_reply(self, club_id: uuid.UUID, discussion_id: uuid.UUID, data, user: User) -> DiscussionReplyResponse:
        await self._check_membership(club_id, user)
        reply = await self.repo.create_reply(
            discussion_id=discussion_id, author_id=user.id,
            content=data.content, parent_reply_id=data.parent_reply_id,
        )
        return DiscussionReplyResponse.model_validate(reply)

    # Invites
    async def create_invite(self, club_id: uuid.UUID, data, user: User) -> BookClubInviteResponse:
        await self._check_club_admin(club_id, user)
        kwargs = {}
        if data.title:
            kwargs["title"] = data.title
        if data.max_uses:
            kwargs["max_uses"] = data.max_uses
        if data.expires_in_days:
            kwargs["expires_at"] = datetime.now(UTC) + timedelta(days=data.expires_in_days)
        invite = await self.repo.create_invite(club_id, user.id, **kwargs)
        return BookClubInviteResponse.model_validate(invite)

    async def list_invites(self, club_id: uuid.UUID, user: User) -> list[BookClubInviteResponse]:
        await self._check_club_admin(club_id, user)
        invites = await self.repo.list_invites(club_id)
        return [BookClubInviteResponse.model_validate(i) for i in invites]

    async def join_via_invite(self, invite_code: str, user: User) -> BookClubMemberResponse:
        invite = await self.repo.get_invite_by_code(invite_code)
        if not invite:
            raise HTTPException(status_code=404, detail="Invalid or expired invite code")
        if invite.expires_at and invite.expires_at < datetime.now(UTC):
            raise HTTPException(status_code=400, detail="Invite code has expired")
        if invite.max_uses and invite.current_uses >= invite.max_uses:
            raise HTTPException(status_code=400, detail="Invite code has reached max uses")

        existing = await self.repo.get_member(invite.club_id, user.id)
        if existing:
            raise HTTPException(status_code=409, detail="Already a member")

        club = await self.repo.get_by_id(invite.club_id)
        count = await self.repo.count_members(invite.club_id)
        if club and count >= club.max_members:
            raise HTTPException(status_code=400, detail="Club is full")

        member = await self.repo.add_member(invite.club_id, user.id, invite_code=invite_code)
        await self.repo.increment_invite_uses(invite.id)
        await self.repo.log_activity(invite.club_id, user.id, "member_joined_via_invite", {"invite_code": invite_code})
        return BookClubMemberResponse.model_validate(member)

    # Activities
    async def list_activities(self, club_id: uuid.UUID, page: int, limit: int):
        activities, total = await self.repo.list_activities(club_id, page, limit)
        return [BookClubActivityResponse.model_validate(a) for a in activities], total

    # Challenges
    async def create_challenge(self, club_id: uuid.UUID, data, user: User) -> BookClubChallengeResponse:
        await self._check_club_admin(club_id, user)
        challenge = await self.repo.create_challenge(club_id=club_id, created_by=user.id, **data.model_dump())
        return BookClubChallengeResponse.model_validate(challenge)

    async def list_challenges(self, club_id: uuid.UUID) -> list[BookClubChallengeResponse]:
        challenges = await self.repo.list_challenges(club_id)
        return [BookClubChallengeResponse.model_validate(c) for c in challenges]

    async def join_challenge(self, club_id: uuid.UUID, challenge_id: uuid.UUID, user: User):
        member = await self._check_membership(club_id, user)
        await self.repo.join_challenge(challenge_id, member.id)

    # Nominations
    async def create_nomination(self, club_id: uuid.UUID, data, user: User) -> NominationResponse:
        await self._check_membership(club_id, user)
        nomination = await self.repo.create_nomination(
            club_id=club_id, book_id=data.book_id,
            nominated_by=user.id, nomination_text=data.nomination_text,
        )
        return NominationResponse.model_validate(nomination)

    async def vote_nomination(self, club_id: uuid.UUID, nomination_id: uuid.UUID, user: User):
        member = await self._check_membership(club_id, user)
        await self.repo.vote_nomination(nomination_id, member.id)

    # Stats
    async def get_stats(self, club_id: uuid.UUID) -> BookClubStatsResponse:
        stats = await self.repo.get_stats(club_id)
        return BookClubStatsResponse(**stats)

    # Access control helpers
    async def _check_membership(self, club_id: uuid.UUID, user: User):
        member = await self.repo.get_member(club_id, user.id)
        if not member and not user.is_admin:
            raise HTTPException(status_code=403, detail="Not a member of this club")
        return member

    async def _check_club_admin(self, club_id: uuid.UUID, user: User):
        club = await self.repo.get_by_id(club_id)
        if not club:
            raise HTTPException(status_code=404, detail="Book club not found")
        if user.is_admin:
            return club
        member = await self.repo.get_member(club_id, user.id)
        if not member or member.role not in ("owner", "admin", "moderator"):
            raise HTTPException(status_code=403, detail="Requires club admin/owner role")
        return club
