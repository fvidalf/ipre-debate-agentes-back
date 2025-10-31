"""add pgvector extension

Revision ID: 67317cf3668e
Revises: e2ea8bfed8b6
Create Date: 2025-10-23 21:25:17.401712

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67317cf3668e'
down_revision: Union[str, None] = 'e2ea8bfed8b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector;")
