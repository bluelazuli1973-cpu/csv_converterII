"""Add is_expense and category to transactions

Revision ID: 20260212_add_tx_fields
Revises: None
Create Date: 2026-02-12
"""
from alembic import op
import sqlalchemy as sa

revision = "20260212_add_tx_fields"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite-safe approach: add columns nullable first, backfill, then enforce NOT NULL using batch mode
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.add_column(sa.Column("is_expense", sa.Boolean(), nullable=True, server_default=sa.text("1")))
        batch_op.add_column(sa.Column("category", sa.String(length=64), nullable=True, server_default="Uncategorized"))

        batch_op.create_index("ix_transactions_is_expense", ["is_expense"])
        batch_op.create_index("ix_transactions_category", ["category"])

    # Backfill existing rows:
    # - expenses are negative amounts (amount < 0)
    # - income otherwise
    op.execute(
        """
        UPDATE transactions
        SET is_expense = CASE WHEN amount < 0 THEN 1 ELSE 0 END
        WHERE is_expense IS NULL
        """
    )
    op.execute(
        """
        UPDATE transactions
        SET category = 'Uncategorized'
        WHERE category IS NULL OR TRIM(category) = ''
        """
    )

    # Enforce NOT NULL (batch mode recreates the table on SQLite)
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.alter_column("is_expense", existing_type=sa.Boolean(), nullable=False)
        batch_op.alter_column("category", existing_type=sa.String(length=64), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_index("ix_transactions_category")
        batch_op.drop_index("ix_transactions_is_expense")

        batch_op.drop_column("category")
        batch_op.drop_column("is_expense")