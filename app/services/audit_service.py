"""Audit service for logging changes."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog, BookAuditLog


class AuditService:
    """Service for audit logging."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_book_change(
        self,
        book_id: uuid.UUID,
        action: str,
        user_id: uuid.UUID | None = None,
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        changes: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> BookAuditLog:
        """Log a book change."""
        log = BookAuditLog(
            book_id=book_id,
            user_id=user_id,
            action=action,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def log_change(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        action: str,
        user_id: uuid.UUID | None = None,
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        changes: dict | None = None,
        metadata: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Log a general change."""
        log = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changes=changes or {},
            audit_metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)
        await self.db.flush()
        return log
