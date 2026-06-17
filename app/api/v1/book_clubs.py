"""Book club API endpoints."""

import uuid

from fastapi import APIRouter, Query

from app.api.v1.deps import CurrentUser, DBSession, OptionalUser
from app.schemas.book_club import (
    BookClubActivityResponse,
    BookClubChallengeCreate,
    BookClubChallengeResponse,
    BookClubCreate,
    BookClubDiscussionCreate,
    BookClubDiscussionResponse,
    BookClubInviteCreate,
    BookClubInviteResponse,
    BookClubMemberResponse,
    BookClubResponse,
    BookClubStatsResponse,
    BookClubUpdate,
    DiscussionReplyCreate,
    DiscussionReplyResponse,
    NominationCreate,
    NominationResponse,
)
from app.schemas.common import PaginatedResponse, create_pagination
from app.services.book_club_service import BookClubService

router = APIRouter()


@router.post("/", response_model=BookClubResponse, status_code=201, summary="Create book club")
async def create_club(data: BookClubCreate, db: DBSession, current_user: CurrentUser) -> BookClubResponse:
    service = BookClubService(db)
    return await service.create_club(data, current_user)


@router.get("/", response_model=PaginatedResponse[BookClubResponse], summary="List book clubs")
async def list_clubs(db: DBSession, current_user: OptionalUser, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), visibility: str | None = None):
    service = BookClubService(db)
    user_id = current_user.id if current_user else None
    clubs, total = await service.list_clubs(user_id, page, limit, visibility)
    return PaginatedResponse(data=clubs, pagination=create_pagination(page, limit, total))


@router.get("/{club_id}", response_model=BookClubResponse, summary="Get book club")
async def get_club(club_id: uuid.UUID, db: DBSession, current_user: OptionalUser) -> BookClubResponse:
    service = BookClubService(db)
    return await service.get_club(club_id, current_user)


@router.put("/{club_id}", response_model=BookClubResponse, summary="Update book club")
async def update_club(club_id: uuid.UUID, data: BookClubUpdate, db: DBSession, current_user: CurrentUser) -> BookClubResponse:
    service = BookClubService(db)
    return await service.update_club(club_id, data, current_user)


@router.delete("/{club_id}", status_code=204, summary="Delete book club")
async def delete_club(club_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> None:
    service = BookClubService(db)
    await service.delete_club(club_id, current_user)


# Members
@router.get("/{club_id}/members", response_model=PaginatedResponse[BookClubMemberResponse], summary="List members")
async def list_members(club_id: uuid.UUID, db: DBSession, current_user: CurrentUser, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    service = BookClubService(db)
    members, total = await service.list_members(club_id, page, limit)
    return PaginatedResponse(data=members, pagination=create_pagination(page, limit, total))


@router.post("/{club_id}/members", response_model=BookClubMemberResponse, status_code=201, summary="Join club")
async def join_club(club_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> BookClubMemberResponse:
    service = BookClubService(db)
    return await service.add_member(club_id, current_user)


@router.put("/{club_id}/members/{user_id}", response_model=BookClubMemberResponse, summary="Update member role")
async def update_member(club_id: uuid.UUID, user_id: uuid.UUID, db: DBSession, current_user: CurrentUser, role: str = Query(...)) -> BookClubMemberResponse:
    service = BookClubService(db)
    return await service.update_member_role(club_id, user_id, role, current_user)


@router.delete("/{club_id}/members/{user_id}", status_code=204, summary="Remove member")
async def remove_member(club_id: uuid.UUID, user_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> None:
    service = BookClubService(db)
    await service.remove_member(club_id, user_id, current_user)


# Books
@router.post("/{club_id}/books", status_code=201, summary="Add book to club")
async def add_book(club_id: uuid.UUID, db: DBSession, current_user: CurrentUser, book_id: uuid.UUID = Query(...)):
    service = BookClubService(db)
    await service.add_book(club_id, book_id, current_user)
    return {"status": "ok"}


@router.get("/{club_id}/books", summary="List club books")
async def list_books(club_id: uuid.UUID, db: DBSession, current_user: CurrentUser, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    service = BookClubService(db)
    books, total = await service.list_books(club_id, page, limit)
    return {"data": [{"book_club_id": b.book_club_id, "book_id": b.book_id, "shared_at": b.shared_at} for b in books], "total": total}


@router.delete("/{club_id}/books/{book_id}", status_code=204, summary="Remove book")
async def remove_book(club_id: uuid.UUID, book_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> None:
    service = BookClubService(db)
    await service.remove_book(club_id, book_id, current_user)


# Discussions
@router.post("/{club_id}/discussions", response_model=BookClubDiscussionResponse, status_code=201, summary="Start discussion")
async def create_discussion(club_id: uuid.UUID, data: BookClubDiscussionCreate, db: DBSession, current_user: CurrentUser) -> BookClubDiscussionResponse:
    service = BookClubService(db)
    return await service.create_discussion(club_id, data, current_user)


@router.get("/{club_id}/discussions", response_model=PaginatedResponse[BookClubDiscussionResponse], summary="List discussions")
async def list_discussions(club_id: uuid.UUID, db: DBSession, current_user: CurrentUser, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    service = BookClubService(db)
    discussions, total = await service.list_discussions(club_id, page, limit)
    return PaginatedResponse(data=discussions, pagination=create_pagination(page, limit, total))


@router.get("/{club_id}/discussions/{discussion_id}", response_model=BookClubDiscussionResponse, summary="Get discussion")
async def get_discussion(club_id: uuid.UUID, discussion_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> BookClubDiscussionResponse:
    service = BookClubService(db)
    return await service.get_discussion(club_id, discussion_id)


@router.post("/{club_id}/discussions/{discussion_id}/replies", response_model=DiscussionReplyResponse, status_code=201, summary="Reply to discussion")
async def create_reply(club_id: uuid.UUID, discussion_id: uuid.UUID, data: DiscussionReplyCreate, db: DBSession, current_user: CurrentUser) -> DiscussionReplyResponse:
    service = BookClubService(db)
    return await service.create_reply(club_id, discussion_id, data, current_user)


# Invites
@router.post("/{club_id}/invites", response_model=BookClubInviteResponse, status_code=201, summary="Generate invite")
async def create_invite(club_id: uuid.UUID, data: BookClubInviteCreate, db: DBSession, current_user: CurrentUser) -> BookClubInviteResponse:
    service = BookClubService(db)
    return await service.create_invite(club_id, data, current_user)


@router.get("/{club_id}/invites", response_model=list[BookClubInviteResponse], summary="List invites")
async def list_invites(club_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> list[BookClubInviteResponse]:
    service = BookClubService(db)
    return await service.list_invites(club_id, current_user)


@router.post("/join/{code}", response_model=BookClubMemberResponse, summary="Join via invite code")
async def join_via_invite(code: str, db: DBSession, current_user: CurrentUser) -> BookClubMemberResponse:
    service = BookClubService(db)
    return await service.join_via_invite(code, current_user)


# Activities
@router.get("/{club_id}/activities", response_model=PaginatedResponse[BookClubActivityResponse], summary="Activity feed")
async def list_activities(club_id: uuid.UUID, db: DBSession, current_user: CurrentUser, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    service = BookClubService(db)
    activities, total = await service.list_activities(club_id, page, limit)
    return PaginatedResponse(data=activities, pagination=create_pagination(page, limit, total))


# Challenges
@router.post("/{club_id}/challenges", response_model=BookClubChallengeResponse, status_code=201, summary="Create challenge")
async def create_challenge(club_id: uuid.UUID, data: BookClubChallengeCreate, db: DBSession, current_user: CurrentUser) -> BookClubChallengeResponse:
    service = BookClubService(db)
    return await service.create_challenge(club_id, data, current_user)


@router.get("/{club_id}/challenges", response_model=list[BookClubChallengeResponse], summary="List challenges")
async def list_challenges(club_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> list[BookClubChallengeResponse]:
    service = BookClubService(db)
    return await service.list_challenges(club_id)


@router.post("/{club_id}/challenges/{challenge_id}/join", status_code=201, summary="Join challenge")
async def join_challenge(club_id: uuid.UUID, challenge_id: uuid.UUID, db: DBSession, current_user: CurrentUser):
    service = BookClubService(db)
    await service.join_challenge(club_id, challenge_id, current_user)
    return {"status": "joined"}


# Nominations
@router.post("/{club_id}/nominations", response_model=NominationResponse, status_code=201, summary="Nominate book")
async def create_nomination(club_id: uuid.UUID, data: NominationCreate, db: DBSession, current_user: CurrentUser) -> NominationResponse:
    service = BookClubService(db)
    return await service.create_nomination(club_id, data, current_user)


@router.post("/{club_id}/nominations/{nomination_id}/vote", status_code=201, summary="Vote on nomination")
async def vote_nomination(club_id: uuid.UUID, nomination_id: uuid.UUID, db: DBSession, current_user: CurrentUser):
    service = BookClubService(db)
    await service.vote_nomination(club_id, nomination_id, current_user)
    return {"status": "voted"}


# Stats
@router.get("/{club_id}/stats", response_model=BookClubStatsResponse, summary="Club statistics")
async def get_stats(club_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> BookClubStatsResponse:
    service = BookClubService(db)
    return await service.get_stats(club_id)
