"""add_book_club_tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-02-12 17:04:00.000000+00:00

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. book_clubs
    op.create_table(
        'book_clubs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tagline', sa.String(500), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('welcome_message', sa.Text(), nullable=True),
        sa.Column('cover_image_url', sa.Text(), nullable=True),
        sa.Column('cover_thumbnail_url', sa.Text(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('visibility', sa.String(20), nullable=False, server_default='public'),
        sa.Column('club_type', sa.String(50), nullable=True),
        sa.Column('max_members', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('member_limit', sa.Integer(), nullable=True),
        sa.Column('is_premium_only', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('featured_book_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('settings', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('premium_features', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_book_clubs_owner_id', 'book_clubs', ['owner_id'])

    # 2. book_club_members
    op.create_table(
        'book_club_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='member'),
        sa.Column('custom_title', sa.String(100), nullable=True),
        sa.Column('rank_title', sa.String(100), nullable=True),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('invite_code', sa.String(50), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['book_club_id'], ['book_clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('book_club_id', 'user_id', name='uq_club_member'),
    )
    op.create_index('idx_club_members_user', 'book_club_members', ['user_id'])

    # 3. book_club_books
    op.create_table(
        'book_club_books',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('shared_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_exclusive', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('shared_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['book_club_id'], ['book_clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['shared_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('book_club_id', 'book_id', name='uq_club_book'),
    )

    # 4. book_club_discussions
    op.create_table(
        'book_club_discussions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('likes_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('replies_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['book_clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_book_club_discussions_club_id', 'book_club_discussions', ['club_id'])

    # 5. book_club_discussion_replies
    op.create_table(
        'book_club_discussion_replies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('discussion_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('parent_reply_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('likes_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['discussion_id'], ['book_club_discussions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_reply_id'], ['book_club_discussion_replies.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_book_club_discussion_replies_discussion_id', 'book_club_discussion_replies', ['discussion_id'])

    # 6. book_club_invites
    op.create_table(
        'book_club_invites',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invite_code', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('current_uses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('invite_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['book_clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invite_code', name='uq_book_club_invite_code'),
    )

    # 7. book_club_activities
    op.create_table(
        'book_club_activities',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('activity_type', sa.String(50), nullable=False),
        sa.Column('activity_data', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('visibility', sa.String(20), nullable=False, server_default='members'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['book_clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_book_club_activities_club_id', 'book_club_activities', ['club_id'])

    # 8. book_club_challenges
    op.create_table(
        'book_club_challenges',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('challenge_type', sa.String(50), nullable=False, server_default='reading'),
        sa.Column('target_value', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('target_unit', sa.String(50), nullable=False, server_default='books'),
        sa.Column('reward_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['book_clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_book_club_challenges_club_id', 'book_club_challenges', ['club_id'])

    # 9. book_club_challenge_participants
    op.create_table(
        'book_club_challenge_participants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('challenge_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('member_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('current_progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_completed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['challenge_id'], ['book_club_challenges.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['member_id'], ['book_club_members.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_book_club_challenge_participants_challenge_id', 'book_club_challenge_participants', ['challenge_id'])

    # 10. book_club_nominations
    op.create_table(
        'book_club_nominations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nominated_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nomination_text', sa.Text(), nullable=True),
        sa.Column('nomination_month', sa.String(7), nullable=True),
        sa.Column('votes_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['book_clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['nominated_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_book_club_nominations_club_id', 'book_club_nominations', ['club_id'])

    # 11. book_club_votes
    op.create_table(
        'book_club_votes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nomination_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('member_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vote_weight', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['nomination_id'], ['book_club_nominations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['member_id'], ['book_club_members.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nomination_id', 'member_id', name='uq_nomination_vote'),
    )

    # 12. book_club_notifications
    op.create_table(
        'book_club_notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('data', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['book_clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_club_notifications_user_read', 'book_club_notifications', ['user_id', 'is_read'])

    # 13. book_club_poster_history
    op.create_table(
        'book_club_poster_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cover_image_url', sa.Text(), nullable=True),
        sa.Column('cover_image_path', sa.Text(), nullable=True),
        sa.Column('cover_thumbnail_url', sa.Text(), nullable=True),
        sa.Column('cover_thumbnail_path', sa.Text(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('image_width', sa.Integer(), nullable=True),
        sa.Column('image_height', sa.Integer(), nullable=True),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('version_notes', sa.Text(), nullable=True),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['book_club_id'], ['book_clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_book_club_poster_history_club_id', 'book_club_poster_history', ['book_club_id'])

    # 14. book_club_exclusive_books
    op.create_table(
        'book_club_exclusive_books',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('added_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('access_level', sa.String(20), nullable=False, server_default='members'),
        sa.Column('minimum_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('minimum_rank', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['club_id'], ['book_clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['added_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_book_club_exclusive_books_club_id', 'book_club_exclusive_books', ['club_id'])

    # 15. book_club_member_stats
    op.create_table(
        'book_club_member_stats',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('book_club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('member_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('books_read', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('books_shared', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('discussions_started', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('comments_posted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('events_attended', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('monthly_points', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('monthly_books_read', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reading_streak_days', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['book_club_id'], ['book_clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['member_id'], ['book_club_members.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('book_club_id', 'member_id', name='uq_club_member_stats'),
    )

    # 16. book_club_achievements
    op.create_table(
        'book_club_achievements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(200), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        sa.Column('points_value', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('requirements', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # 17. book_club_member_achievements
    op.create_table(
        'book_club_member_achievements',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('achievement_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('member_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('earned_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['achievement_id'], ['book_club_achievements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['member_id'], ['book_club_members.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['club_id'], ['book_clubs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('achievement_id', 'member_id', name='uq_member_achievement'),
    )


def downgrade() -> None:
    op.drop_table('book_club_member_achievements')
    op.drop_table('book_club_achievements')
    op.drop_table('book_club_member_stats')
    op.drop_index('idx_book_club_exclusive_books_club_id', table_name='book_club_exclusive_books')
    op.drop_table('book_club_exclusive_books')
    op.drop_index('idx_book_club_poster_history_club_id', table_name='book_club_poster_history')
    op.drop_table('book_club_poster_history')
    op.drop_index('idx_club_notifications_user_read', table_name='book_club_notifications')
    op.drop_table('book_club_notifications')
    op.drop_table('book_club_votes')
    op.drop_index('idx_book_club_nominations_club_id', table_name='book_club_nominations')
    op.drop_table('book_club_nominations')
    op.drop_index('idx_book_club_challenge_participants_challenge_id', table_name='book_club_challenge_participants')
    op.drop_table('book_club_challenge_participants')
    op.drop_index('idx_book_club_challenges_club_id', table_name='book_club_challenges')
    op.drop_table('book_club_challenges')
    op.drop_index('idx_book_club_activities_club_id', table_name='book_club_activities')
    op.drop_table('book_club_activities')
    op.drop_table('book_club_invites')
    op.drop_index('idx_book_club_discussion_replies_discussion_id', table_name='book_club_discussion_replies')
    op.drop_table('book_club_discussion_replies')
    op.drop_index('idx_book_club_discussions_club_id', table_name='book_club_discussions')
    op.drop_table('book_club_discussions')
    op.drop_table('book_club_books')
    op.drop_index('idx_club_members_user', table_name='book_club_members')
    op.drop_table('book_club_members')
    op.drop_index('idx_book_clubs_owner_id', table_name='book_clubs')
    op.drop_table('book_clubs')
