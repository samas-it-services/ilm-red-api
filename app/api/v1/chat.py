"""Chat API endpoints for AI conversations."""

import json
from uuid import UUID

from fastapi import APIRouter, Query, status
from fastapi.responses import StreamingResponse

from app.api.v1.deps import CurrentUser, DBSession
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageListResponse,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatSessionUpdate,
    MessageFeedbackCreate,
    MessageFeedbackResponse,
)
from app.services.chat_service import ChatService

router = APIRouter()


# Session endpoints


@router.post(
    "",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create chat session",
    description="Create a new AI chat session, optionally linked to a book.",
)
async def create_session(
    db: DBSession,
    current_user: CurrentUser,
    data: ChatSessionCreate,
) -> ChatSessionResponse:
    """Create a new chat session.

    - **title**: Optional session title
    - **book_id**: Optional book ID for book-specific discussions

    If a book_id is provided, the AI will have context about that book.
    """
    service = ChatService(db)
    return await service.create_session(current_user, data)


@router.get(
    "",
    response_model=ChatSessionListResponse,
    summary="List chat sessions",
    description="List your chat sessions with optional filtering.",
)
async def list_sessions(
    db: DBSession,
    current_user: CurrentUser,
    book_id: UUID | None = Query(None, description="Filter by book ID"),
    include_archived: bool = Query(False, description="Include archived sessions"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, alias="page_size", description="Items per page"),
) -> ChatSessionListResponse:
    """List chat sessions with filtering and pagination.

    Sessions are sorted by last update time (most recent first).
    """
    service = ChatService(db)
    return await service.list_sessions(
        user=current_user,
        book_id=book_id,
        include_archived=include_archived,
        page=page,
        limit=limit,
    )


@router.get(
    "/{session_id}",
    response_model=ChatSessionDetail,
    summary="Get chat session",
    description="Get a chat session with all its messages.",
)
async def get_session(
    session_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ChatSessionDetail:
    """Get a chat session with all messages.

    Returns the session details along with the complete conversation history.
    """
    service = ChatService(db)
    return await service.get_session(
        session_id=session_id,
        user=current_user,
        include_messages=True,
    )


@router.put(
    "/{session_id}",
    response_model=ChatSessionResponse,
    summary="Update chat session",
    description="Update chat session metadata (title).",
)
async def update_session(
    session_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    data: ChatSessionUpdate,
) -> ChatSessionResponse:
    """Update a chat session.

    - **title**: New session title
    """
    service = ChatService(db)
    return await service.update_session(
        session_id=session_id,
        user=current_user,
        data=data,
    )


@router.post(
    "/{session_id}/archive",
    response_model=ChatSessionResponse,
    summary="Archive chat session",
    description="Archive a chat session (soft delete).",
)
async def archive_session(
    session_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> ChatSessionResponse:
    """Archive a chat session.

    Archived sessions are hidden from the default list but can be retrieved
    by setting include_archived=true.
    """
    service = ChatService(db)
    return await service.archive_session(
        session_id=session_id,
        user=current_user,
    )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete chat session",
    description="Permanently delete a chat session and all its messages.",
)
async def delete_session(
    session_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Delete a chat session permanently.

    This action cannot be undone. All messages in the session will be deleted.
    """
    service = ChatService(db)
    await service.delete_session(
        session_id=session_id,
        user=current_user,
    )


# Message endpoints


@router.post(
    "/{session_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send message",
    description="Send a message and receive an AI response (non-streaming).",
)
async def send_message(
    session_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    data: ChatMessageCreate,
) -> ChatMessageResponse:
    """Send a message to the AI.

    - **content**: Your message text
    - **model**: Optional model override (e.g., 'gpt-4o-mini', 'claude-3-haiku')

    Returns the AI's response. For streaming responses, use the /stream endpoint.
    """
    service = ChatService(db)
    return await service.send_message(
        session_id=session_id,
        user=current_user,
        data=data,
    )


@router.get(
    "/{session_id}/messages",
    response_model=ChatMessageListResponse,
    summary="Get messages",
    description="Get messages from a chat session with pagination.",
)
async def get_messages(
    session_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, alias="page_size", description="Items per page"),
) -> ChatMessageListResponse:
    """Get messages from a chat session.

    Messages are returned in chronological order (oldest first).
    """
    service = ChatService(db)
    return await service.get_messages(
        session_id=session_id,
        user=current_user,
        page=page,
        limit=limit,
    )


@router.post(
    "/{session_id}/stream",
    summary="Stream message",
    description="Send a message and stream the AI response via Server-Sent Events (SSE).",
    responses={
        200: {
            "description": "SSE stream of response chunks",
            "content": {
                "text/event-stream": {
                    "schema": {
                        "type": "string",
                        "description": "SSE stream with JSON data chunks",
                    }
                }
            },
        }
    },
)
async def stream_message(
    session_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    data: ChatMessageCreate,
) -> StreamingResponse:
    """Stream an AI response via Server-Sent Events.

    - **content**: Your message text
    - **model**: Optional model override

    The response is a stream of Server-Sent Events:
    - `type: "content"` - Partial response content
    - `type: "done"` - Final message with token counts and cost
    - `type: "error"` - Error occurred during streaming

    Example SSE events:
    ```
    data: {"type": "content", "content": "Hello"}

    data: {"type": "content", "content": ", how can"}

    data: {"type": "done", "message_id": "...", "tokens_input": 50, "tokens_output": 100}
    ```
    """
    service = ChatService(db)

    async def event_generator():
        async for chunk in service.stream_message(
            session_id=session_id,
            user=current_user,
            data=data,
        ):
            # Format as SSE
            yield f"data: {json.dumps(chunk.model_dump())}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# Feedback endpoints


@router.post(
    "/{session_id}/messages/{message_id}/feedback",
    response_model=MessageFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit message feedback",
    description="Submit thumbs up/down feedback on an AI message.",
)
async def submit_feedback(
    session_id: UUID,
    message_id: UUID,
    db: DBSession,
    current_user: CurrentUser,
    data: MessageFeedbackCreate,
) -> MessageFeedbackResponse:
    """Submit feedback on an AI message.

    - **rating**: 1 for thumbs up, -1 for thumbs down
    - **comment**: Optional comment explaining the rating

    This helps improve AI responses over time.
    """
    service = ChatService(db)
    return await service.submit_feedback(
        session_id=session_id,
        message_id=message_id,
        user=current_user,
        data=data,
    )
