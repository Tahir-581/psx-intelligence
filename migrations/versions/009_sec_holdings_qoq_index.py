"""Add QoQ lookup index on sec_holdings

Revision ID: 009_sec_holdings_qoq_index
Revises: 008_sec_smart_money
Create Date: 2026-06-18

"""

from typing import Sequence, Union

from alembic import op

revision: str = "009_sec_holdings_qoq_index"
down_revision: Union[str, None] = "008_sec_smart_money"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_sec_holdings_qoq_lookup",
        "sec_holdings",
        ["report_period", "cik", "cusip", "name_of_issuer"],
    )


def downgrade() -> None:
    op.drop_index("idx_sec_holdings_qoq_lookup", table_name="sec_holdings")
