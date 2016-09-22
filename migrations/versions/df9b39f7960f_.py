"""Start modelling dataset inheritance

Revision ID: df9b39f7960f
Revises: 1c914ed5374f
Create Date: 2016-09-22 09:43:45.291386

"""

# revision identifiers, used by Alembic.
revision = 'df9b39f7960f'
down_revision = '1c914ed5374f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('taxons',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('samplescans',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('taxon_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['id'], ['datasets.id'], ),
    sa.ForeignKeyConstraint(['taxon_id'], ['taxons.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column(u'datasets', sa.Column('type', sa.String(length=50), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column(u'datasets', 'type')
    op.drop_table('samplescans')
    op.drop_table('taxons')
    ### end Alembic commands ###
