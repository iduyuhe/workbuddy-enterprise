"""initial marketplace schema

Revision ID: 0001_initial_marketplace
Revises:
Create Date: 2026-08-13 10:00:00.000000

packages / package_versions / package_installs / package_reviews
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial_marketplace'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# JSON 列：PG 用 jsonb（支持 @> 包含查询），其余方言用 json
JSONCol = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    op.create_table('packages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('slug', sa.String(length=160), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('package_type', sa.String(length=20), nullable=False),
        sa.Column('publisher', sa.String(length=160), nullable=False),
        sa.Column('summary', sa.String(length=280), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('license', sa.String(length=60), nullable=True),
        sa.Column('price_model', sa.String(length=20), nullable=False),
        sa.Column('price_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False),
        sa.Column('tags', JSONCol, nullable=True),
        sa.Column('categories', JSONCol, nullable=True),
        sa.Column('homepage', sa.String(length=512), nullable=True),
        sa.Column('repository', sa.String(length=512), nullable=True),
        sa.Column('icon_url', sa.String(length=512), nullable=True),
        sa.Column('supported_platforms', JSONCol, nullable=True),
        sa.Column('version', sa.String(length=32), nullable=False),
        sa.Column('install_count', sa.Integer(), nullable=False),
        sa.Column('rating_avg', sa.Float(), nullable=False),
        sa.Column('rating_count', sa.Integer(), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=True),
        sa.Column('owner_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_packages_slug', 'packages', ['slug'], unique=True)
    op.create_index('ix_packages_package_type', 'packages', ['package_type'], unique=False)
    op.create_index('ix_packages_publisher', 'packages', ['publisher'], unique=False)
    op.create_index('ix_packages_tenant_id', 'packages', ['tenant_id'], unique=False)
    op.create_index('ix_packages_owner_id', 'packages', ['owner_id'], unique=False)

    op.create_table('package_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('package_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.String(length=32), nullable=False),
        sa.Column('manifest', JSONCol, nullable=True),
        sa.Column('changelog', sa.Text(), nullable=True),
        sa.Column('download_url', sa.String(length=512), nullable=True),
        sa.Column('artifact_hash', sa.String(length=128), nullable=True),
        sa.Column('min_platform_version', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['package_id'], ['packages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('package_id', 'version', name='uq_package_version'),
    )

    op.create_table('package_installs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('package_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('installed_by', sa.UUID(), nullable=True),
        sa.Column('version', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['package_id'], ['packages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('package_id', 'tenant_id', name='uq_package_tenant'),
    )
    op.create_index('ix_package_installs_tenant_id', 'package_installs', ['tenant_id'], unique=False)
    op.create_index('ix_package_installs_installed_by', 'package_installs', ['installed_by'], unique=False)

    op.create_table('package_reviews',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('package_id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=True),
        sa.Column('reviewer_id', sa.UUID(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=160), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['package_id'], ['packages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_package_reviews_tenant_id', 'package_reviews', ['tenant_id'], unique=False)
    op.create_index('ix_package_reviews_reviewer_id', 'package_reviews', ['reviewer_id'], unique=False)


def downgrade() -> None:
    op.drop_table('package_reviews')
    op.drop_table('package_installs')
    op.drop_table('package_versions')
    op.drop_index('ix_packages_owner_id', table_name='packages')
    op.drop_index('ix_packages_tenant_id', table_name='packages')
    op.drop_index('ix_packages_publisher', table_name='packages')
    op.drop_index('ix_packages_package_type', table_name='packages')
    op.drop_index('ix_packages_slug', table_name='packages')
    op.drop_table('packages')
