"""
Add build.untagged column

Create Date: 2017-11-17 15:38:12.009414

"""

# revision identifiers, used by Alembic.
revision = '8175c5b109d9'
down_revision = '245edb2e0764'

from alembic import op


def upgrade():
    op.execute("""
        ALTER TABLE build ADD COLUMN untagged boolean;
        ALTER TABLE build ALTER COLUMN untagged SET DEFAULT FALSE;
        UPDATE build SET untagged = FALSE;
        ALTER TABLE build ALTER COLUMN untagged SET NOT NULL;
    """)


def downgrade():
    op.execute("""
        ALTER TABLE build DROP COLUMN untagged;
    """)
