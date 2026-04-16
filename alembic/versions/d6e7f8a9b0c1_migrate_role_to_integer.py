"""migrate role to integer

Revision ID: d6e7f8a9b0c1
Revises: c5d3e6f7a8b9
Create Date: 2026-04-16 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd6e7f8a9b0c1'
down_revision = 'c5d3e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade():
    # Add temporary integer column
    op.add_column('user', sa.Column('role_int', sa.Integer(), nullable=True))

    # Map string roles to integers
    op.execute("""
        UPDATE "user" SET role_int = CASE role
            WHEN 'R' THEN 1
            WHEN 'A' THEN 2
            WHEN 'B' THEN 3
            WHEN 'C' THEN 4
            WHEN 'D' THEN 5
            ELSE 4
        END
    """)

    # Drop old column, rename new one
    op.drop_column('user', 'role')
    op.alter_column('user', 'role_int', new_column_name='role')

    # Set default
    op.alter_column('user', 'role', server_default='4')


def downgrade():
    # Add temporary string column
    op.add_column('user', sa.Column('role_str', sa.String(4), nullable=True))

    # Map integers back to strings
    op.execute("""
        UPDATE "user" SET role_str = CASE role
            WHEN 1 THEN 'R'
            WHEN 2 THEN 'A'
            WHEN 3 THEN 'B'
            WHEN 4 THEN 'C'
            WHEN 5 THEN 'D'
            ELSE 'C'
        END
    """)

    # Drop old column, rename new one
    op.drop_column('user', 'role')
    op.alter_column('user', 'role_str', new_column_name='role')

    # Set default
    op.alter_column('user', 'role', server_default='C')
