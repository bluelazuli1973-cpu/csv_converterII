"""Add is_financial_transaction to transactions

Revision ID: 20260213_add_is_financial_transaction
Revises: 20260212_add_tx_fields
Create Date: 2026-02-13
"""
from alembic import op
import sqlalchemy as sa

revision = "20260213_add_is_financial_transaction"
down_revision = "20260212_add_tx_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_financial_transaction",
                sa.Boolean(),
                nullable=True,
                server_default=sa.text("0"),
            )
        )
        batch_op.create_index(
            "ix_transactions_is_financial_transaction",
            ["is_financial_transaction"],
        )

    # Backfill for existing rows based on text match in description/place_purchase
    op.execute(
        """
        UPDATE transactions
        SET is_financial_transaction =
          CASE
            WHEN lower(coalesce(description, '')) LIKE '%överföring%'
              OR lower(coalesce(description, '')) LIKE '%lön%'
              OR lower(coalesce(place_purchase, '')) LIKE '%överföring%'
              OR lower(coalesce(place_purchase, '')) LIKE '%lön%'
            THEN 1 ELSE 0
          END
        WHERE is_financial_transaction IS NULL
        """
    )

    with op.batch_alter_table("transactions") as batch_op:
        batch_op.alter_column(
            "is_financial_transaction",
            existing_type=sa.Boolean(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_index("ix_transactions_is_financial_transaction")
        batch_op.drop_column("is_financial_transaction")
