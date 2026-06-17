"""Audit repository for database operations."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog, BookAuditLog


class AuditRepository:
    """Repository for audit log database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_book_audit_logs(
        self, book_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> tuple[list[BookAuditLog], int]:
        """Get audit logs for a book."""
        count_stmt = (
            select(func.count())
            .select_from(BookAuditLog)
            .where(BookAuditLog.book_id == book_id)
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(BookAuditLog)
            .where(BookAuditLog.book_id == book_id)
            .order_by(BookAuditLog.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_entity_audit_logs(
        self, entity_type: str, entity_id: uuid.UUID, page: int = 1, limit: int = 20
    ) -> tuple[list[AuditLog], int]:
        """Get audit logs for any entity."""
        count_stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total
