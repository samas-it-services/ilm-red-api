"""Chat service for AI conversation business logic."""

import uuid
from collections.abc import AsyncIterator

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import (
    DEFAULT_MODEL_PRIVATE,
    DEFAULT_MODEL_PUBLIC,
    FREE_TIER_MODELS,
    MODEL_REGISTRY,
    AIProviderError,
    RateLimitError,
    get_model_config,
    get_provider_for_model,
)
from app.ai import (
    ChatMessage as AIChatMessage,
)
from app.models.book import Book
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.repositories.book_repo import BookRepository
from app.repositories.chat_repo import ChatRepository
from app.schemas.chat import (
    BookBrief,
    ChatMessageCreate,
    ChatMessageListResponse,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionDetail,
    ChatSessionListItem,
    ChatSessionListResponse,
    ChatSessionResponse,
    ChatSessionUpdate,
    MessageFeedbackCreate,
    MessageFeedbackResponse,
    StreamChunk,
)
from app.schemas.common import create_pagination

logger = structlog.get_logger(__name__)


class ChatService:
    """Service for chat-related business logic."""

    # Maximum messages to include in AI context
    MAX_CONTEXT_MESSAGES = 20

    # Default system prompt for book-related chats
    BOOK_SYSTEM_PROMPT = """You are a helpful AI assistant discussing a book.
The user is reading "{title}" by {author}.
Help them understand the content, answer questions about the book,
and provide relevant insights. Be educational and supportive."""

    # Default system prompt for general chats
    GENERAL_SYSTEM_PROMPT = """You are a helpful AI assistant for a digital library platform.
Help users with their questions about books, reading, learning, and related topics.
Be educational, supportive, and encouraging."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.chat_repo = ChatRepository(db)
        self.book_repo = BookRepository(db)

    # Session management

    async def create_session(
        self,
        user: User,
        data: ChatSessionCreate,
    ) -> ChatSessionResponse:
        """Create a new chat session.

        Args:
            user: Current user
            data: Session creation data

        Returns:
            Created session response

        Raises:
            HTTPException: If book not found or not accessible
        """
        book = None
        if data.book_id:
            # Verify book exists and user has access
            book = await self.book_repo.get_by_id(data.book_id)
            if not book:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Book not found",
                )
            # Check visibility
            if book.visibility == "private" and book.owner_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have access to this book",
                )

        session = await self.chat_repo.create_session(
            user_id=user.id,
            title=data.title,
            book_id=data.book_id,
        )

        logger.info(
            "chat_session_created",
            session_id=str(session.id),
            user_id=str(user.id),
            book_id=str(data.book_id) if data.book_id else None,
        )

        return self._session_to_response(session, book)

    async def get_session(
        self,
        session_id: uuid.UUID,
        user: User,
        include_messages: bool = False,
    ) -> ChatSessionResponse | ChatSessionDetail:
        """Get a chat session.

        Args:
            session_id: Session ID
            user: Current user
            include_messages: Whether to include messages

        Returns:
            Session response (with or without messages)

        Raises:
            HTTPException: If session not found
        """
        session = await self.chat_repo.get_session(
            session_id=session_id,
            user_id=user.id,
            include_book=True,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        if include_messages:
            messages, _ = await self.chat_repo.get_messages(
                session_id=session_id,
                page=1,
                limit=1000,  # Get all messages for session detail
            )
            return self._session_to_detail(session, messages)

        return self._session_to_response(session)

    async def list_sessions(
        self,
        user: User,
        book_id: uuid.UUID | None = None,
        include_archived: bool = False,
        page: int = 1,
        limit: int = 20,
    ) -> ChatSessionListResponse:
        """List chat sessions for a user.

        Args:
            user: Current user
            book_id: Optional filter by book
            include_archived: Include archived sessions
            page: Page number
            limit: Items per page

        Returns:
            Paginated session list
        """
        sessions, total = await self.chat_repo.list_sessions(
            user_id=user.id,
            book_id=book_id,
            include_archived=include_archived,
            page=page,
            limit=limit,
        )

        # Get last message previews
        items = []
        for session in sessions:
            preview = await self.chat_repo.get_last_message_preview(session.id)
            items.append(
                ChatSessionListItem(
                    id=session.id,
                    title=session.title,
                    book_id=session.book_id,
                    message_count=session.message_count,
                    last_model=session.last_model,
                    is_archived=session.is_archived,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    last_message_preview=preview,
                )
            )

        return ChatSessionListResponse(
            data=items,
            pagination=create_pagination(page, limit, total),
        )

    async def update_session(
        self,
        session_id: uuid.UUID,
        user: User,
        data: ChatSessionUpdate,
    ) -> ChatSessionResponse:
        """Update a chat session.

        Args:
            session_id: Session ID
            user: Current user
            data: Update data

        Returns:
            Updated session response

        Raises:
            HTTPException: If session not found
        """
        session = await self.chat_repo.get_session(
            session_id=session_id,
            user_id=user.id,
            include_book=True,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        session = await self.chat_repo.update_session(
            session=session,
            title=data.title,
        )

        return self._session_to_response(session)

    async def archive_session(
        self,
        session_id: uuid.UUID,
        user: User,
    ) -> ChatSessionResponse:
        """Archive a chat session.

        Args:
            session_id: Session ID
            user: Current user

        Returns:
            Updated session response

        Raises:
            HTTPException: If session not found
        """
        session = await self.chat_repo.get_session(
            session_id=session_id,
            user_id=user.id,
            include_book=True,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        session = await self.chat_repo.archive_session(session)

        logger.info(
            "chat_session_archived",
            session_id=str(session.id),
            user_id=str(user.id),
        )

        return self._session_to_response(session)

    async def delete_session(
        self,
        session_id: uuid.UUID,
        user: User,
    ) -> None:
        """Delete a chat session.

        Args:
            session_id: Session ID
            user: Current user

        Raises:
            HTTPException: If session not found
        """
        session = await self.chat_repo.get_session(
            session_id=session_id,
            user_id=user.id,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        await self.chat_repo.delete_session(session)

        logger.info(
            "chat_session_deleted",
            session_id=str(session_id),
            user_id=str(user.id),
        )

    # Message handling

    async def send_message(
        self,
        session_id: uuid.UUID,
        user: User,
        data: ChatMessageCreate,
    ) -> ChatMessageResponse:
        """Send a message and get AI response (non-streaming).

        Args:
            session_id: Session ID
            user: Current user
            data: Message data

        Returns:
            AI response message

        Raises:
            HTTPException: If session not found or AI error
        """
        session = await self.chat_repo.get_session(
            session_id=session_id,
            user_id=user.id,
            include_book=True,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        # Select model
        model_id = self._select_model(
            user=user,
            book=session.book,
            requested_model=data.model,
        )

        # Save user message
        await self.chat_repo.create_message(
            session_id=session_id,
            role="user",
            content=data.content,
        )
        await self.chat_repo.update_session_after_message(session_id)

        # Get conversation history
        history = await self.chat_repo.get_session_history(
            session_id=session_id,
            limit=self.MAX_CONTEXT_MESSAGES,
        )

        # Build AI messages
        ai_messages = self._build_ai_messages(history, session.book)

        # Get AI response
        try:
            provider = get_provider_for_model(model_id)
            model_config = get_model_config(model_id)

            response = await provider.chat(
                messages=ai_messages,
                model=model_config.model_id,
                max_tokens=4096,
                temperature=0.7,
                system_prompt=self._get_system_prompt(session.book),
            )

            # Calculate cost in cents
            cost_cents = int(response.cost_usd * 100)

            # Save assistant message
            assistant_message = await self.chat_repo.create_message(
                session_id=session_id,
                role="assistant",
                content=response.content,
                model=model_id,
                tokens_input=response.prompt_tokens,
                tokens_output=response.completion_tokens,
                cost_cents=cost_cents,
                finish_reason=response.finish_reason,
            )
            await self.chat_repo.update_session_after_message(
                session_id=session_id,
                model=model_id,
            )

            logger.info(
                "chat_message_completed",
                session_id=str(session_id),
                user_id=str(user.id),
                model=model_id,
                tokens_input=response.prompt_tokens,
                tokens_output=response.completion_tokens,
                cost_cents=cost_cents,
            )

            return self._message_to_response(assistant_message)

        except RateLimitError as e:
            logger.warning(
                "ai_rate_limit",
                session_id=str(session_id),
                model=model_id,
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="AI service is temporarily unavailable. Please try again later.",
            )
        except AIProviderError as e:
            logger.error(
                "ai_provider_error",
                session_id=str(session_id),
                model=model_id,
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service error. Please try again.",
            )

    async def stream_message(
        self,
        session_id: uuid.UUID,
        user: User,
        data: ChatMessageCreate,
    ) -> AsyncIterator[StreamChunk]:
        """Send a message and stream AI response via SSE.

        Args:
            session_id: Session ID
            user: Current user
            data: Message data

        Yields:
            StreamChunk objects for SSE

        Raises:
            HTTPException: If session not found
        """
        session = await self.chat_repo.get_session(
            session_id=session_id,
            user_id=user.id,
            include_book=True,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        # Select model
        model_id = self._select_model(
            user=user,
            book=session.book,
            requested_model=data.model,
        )

        # Check if model supports streaming
        model_config = get_model_config(model_id)
        if not model_config.supports_streaming:
            # Fall back to non-streaming
            response = await self.send_message(session_id, user, data)
            yield StreamChunk(
                type="content",
                content=response.content,
            )
            yield StreamChunk(
                type="done",
                message_id=response.id,
                tokens_input=response.tokens_input,
                tokens_output=response.tokens_output,
                cost_cents=response.cost_cents,
                model=response.model,
                finish_reason=response.finish_reason,
            )
            return

        # Save user message
        await self.chat_repo.create_message(
            session_id=session_id,
            role="user",
            content=data.content,
        )
        await self.chat_repo.update_session_after_message(session_id)

        # Get conversation history
        history = await self.chat_repo.get_session_history(
            session_id=session_id,
            limit=self.MAX_CONTEXT_MESSAGES,
        )

        # Build AI messages
        ai_messages = self._build_ai_messages(history, session.book)

        # Create placeholder for assistant message
        assistant_message = await self.chat_repo.create_message(
            session_id=session_id,
            role="assistant",
            content="",  # Will be updated as we stream
            model=model_id,
        )
        await self.chat_repo.update_session_after_message(
            session_id=session_id,
            model=model_id,
        )

        # Stream response
        full_content = []
        try:
            provider = get_provider_for_model(model_id)

            async for chunk in provider.chat_stream(
                messages=ai_messages,
                model=model_config.model_id,
                max_tokens=4096,
                temperature=0.7,
                system_prompt=self._get_system_prompt(session.book),
            ):
                full_content.append(chunk)
                yield StreamChunk(type="content", content=chunk)

            # Update message with full content
            final_content = "".join(full_content)

            # Estimate tokens (rough estimate: ~4 chars per token)
            estimated_output_tokens = len(final_content) // 4
            estimated_input_tokens = sum(len(m.content) for m in ai_messages) // 4
            cost_cents = int(
                model_config.calculate_cost(
                    estimated_input_tokens,
                    estimated_output_tokens,
                )
                * 100
            )

            await self.chat_repo.update_message(
                message=assistant_message,
                content=final_content,
                tokens_input=estimated_input_tokens,
                tokens_output=estimated_output_tokens,
                cost_cents=cost_cents,
                finish_reason="stop",
            )

            yield StreamChunk(
                type="done",
                message_id=assistant_message.id,
                tokens_input=estimated_input_tokens,
                tokens_output=estimated_output_tokens,
                cost_cents=cost_cents,
                model=model_id,
                finish_reason="stop",
            )

            logger.info(
                "chat_stream_completed",
                session_id=str(session_id),
                user_id=str(user.id),
                model=model_id,
                tokens_output=estimated_output_tokens,
            )

        except Exception as e:
            logger.error(
                "chat_stream_error",
                session_id=str(session_id),
                error=str(e),
            )
            yield StreamChunk(type="error", error=str(e))

    async def get_messages(
        self,
        session_id: uuid.UUID,
        user: User,
        page: int = 1,
        limit: int = 50,
    ) -> ChatMessageListResponse:
        """Get messages for a session.

        Args:
            session_id: Session ID
            user: Current user
            page: Page number
            limit: Items per page

        Returns:
            Paginated message list

        Raises:
            HTTPException: If session not found
        """
        session = await self.chat_repo.get_session(
            session_id=session_id,
            user_id=user.id,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        messages, total = await self.chat_repo.get_messages(
            session_id=session_id,
            page=page,
            limit=limit,
        )

        return ChatMessageListResponse(
            data=[self._message_to_response(m) for m in messages],
            pagination=create_pagination(page, limit, total),
        )

    # Feedback handling

    async def submit_feedback(
        self,
        session_id: uuid.UUID,
        message_id: uuid.UUID,
        user: User,
        data: MessageFeedbackCreate,
    ) -> MessageFeedbackResponse:
        """Submit feedback on a message.

        Args:
            session_id: Session ID
            message_id: Message ID
            user: Current user
            data: Feedback data

        Returns:
            Created feedback

        Raises:
            HTTPException: If session/message not found
        """
        # Verify session ownership
        session = await self.chat_repo.get_session(
            session_id=session_id,
            user_id=user.id,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found",
            )

        # Verify message exists in session
        message = await self.chat_repo.get_message(
            message_id=message_id,
            session_id=session_id,
        )

        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )

        # Only allow feedback on assistant messages
        if message.role != "assistant":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only provide feedback on assistant messages",
            )

        feedback = await self.chat_repo.create_feedback(
            message_id=message_id,
            user_id=user.id,
            rating=data.rating,
            comment=data.comment,
        )

        logger.info(
            "message_feedback_submitted",
            message_id=str(message_id),
            user_id=str(user.id),
            rating=data.rating,
        )

        return MessageFeedbackResponse(
            id=feedback.id,
            message_id=feedback.message_id,
            rating=feedback.rating,
            comment=feedback.comment,
            created_at=feedback.created_at,
        )

    # Helper methods

    def _select_model(
        self,
        user: User,
        book: Book | None,
        requested_model: str | None,
    ) -> str:
        """Select the appropriate model for a request.

        Args:
            user: Current user
            book: Optional book context
            requested_model: User's requested model (if any)

        Returns:
            Model ID to use
        """
        # If user requested a specific model, validate it
        if requested_model:
            if requested_model not in MODEL_REGISTRY:
                logger.warning(
                    "invalid_model_requested",
                    requested=requested_model,
                    user_id=str(user.id),
                )
                # Fall through to default selection
            else:
                # Check if user can access this model (free tier check)
                # TODO: Add premium tier check when billing is implemented
                if requested_model not in FREE_TIER_MODELS:
                    logger.warning(
                        "premium_model_requested_by_free_user",
                        requested=requested_model,
                        user_id=str(user.id),
                    )
                    # Fall through to default
                else:
                    return requested_model

        # Default model selection based on book visibility
        if book and book.visibility == "public":
            return DEFAULT_MODEL_PUBLIC
        return DEFAULT_MODEL_PRIVATE

    def _get_system_prompt(self, book: Book | None) -> str:
        """Get the system prompt for the conversation.

        Args:
            book: Optional book context

        Returns:
            System prompt string
        """
        if book:
            return self.BOOK_SYSTEM_PROMPT.format(
                title=book.title,
                author=book.author or "Unknown",
            )
        return self.GENERAL_SYSTEM_PROMPT

    def _build_ai_messages(
        self,
        history: list[ChatMessage],
        book: Book | None,
    ) -> list[AIChatMessage]:
        """Build AI message list from chat history.

        Args:
            history: Chat message history
            book: Optional book context

        Returns:
            List of AI ChatMessage objects
        """
        return [
            AIChatMessage(role=msg.role, content=msg.content)
            for msg in history
            if msg.role in ("user", "assistant", "system")
        ]

    def _session_to_response(
        self,
        session: ChatSession,
        book: Book | None = None,
    ) -> ChatSessionResponse:
        """Convert session model to response schema.

        Args:
            session: ChatSession model
            book: Optional book (if not loaded via relationship)

        Returns:
            ChatSessionResponse
        """
        book_obj = book or session.book
        book_brief = None
        if book_obj:
            book_brief = BookBrief(
                id=book_obj.id,
                title=book_obj.title,
                author=book_obj.author,
                cover_url=book_obj.cover_url,
            )

        return ChatSessionResponse(
            id=session.id,
            title=session.title,
            book_id=session.book_id,
            book=book_brief,
            message_count=session.message_count,
            last_model=session.last_model,
            is_archived=session.is_archived,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    def _session_to_detail(
        self,
        session: ChatSession,
        messages: list[ChatMessage],
    ) -> ChatSessionDetail:
        """Convert session model to detail response.

        Args:
            session: ChatSession model
            messages: List of messages

        Returns:
            ChatSessionDetail
        """
        book_brief = None
        if session.book:
            book_brief = BookBrief(
                id=session.book.id,
                title=session.book.title,
                author=session.book.author,
                cover_url=session.book.cover_url,
            )

        return ChatSessionDetail(
            id=session.id,
            title=session.title,
            book_id=session.book_id,
            book=book_brief,
            message_count=session.message_count,
            last_model=session.last_model,
            is_archived=session.is_archived,
            created_at=session.created_at,
            updated_at=session.updated_at,
            messages=[self._message_to_response(m) for m in messages],
        )

    def _message_to_response(self, message: ChatMessage) -> ChatMessageResponse:
        """Convert message model to response schema.

        Args:
            message: ChatMessage model

        Returns:
            ChatMessageResponse
        """
        return ChatMessageResponse(
            id=message.id,
            session_id=message.session_id,
            role=message.role,
            content=message.content,
            tokens_input=message.tokens_input,
            tokens_output=message.tokens_output,
            cost_cents=message.cost_cents,
            model=message.model,
            finish_reason=message.finish_reason,
            safety_flags=message.safety_flags,
            created_at=message.created_at,
            has_feedback=message.feedback is not None if hasattr(message, 'feedback') else False,
        )
