"""empty message

Revision ID: a503c0d125e7
Revises: f01abbca82ed
Create Date: 2017-08-29 15:17:10.189374

"""

# revision identifiers, used by Alembic.
revision = 'a503c0d125e7'
down_revision = 'f01abbca82ed'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    naming_convention = {
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    }
    with op.batch_alter_table('direct_access', naming_convention=naming_convention, schema=None) as batch_op:
        batch_op.drop_constraint('fk_direct_access_collection_id_collections', type_='foreignkey')
        batch_op.drop_column('collection_id')

    with op.batch_alter_table('permissions', naming_convention=naming_convention, schema=None) as batch_op:
        batch_op.drop_constraint('fk_permissions_collection_id_collections', type_='foreignkey')
        batch_op.drop_column('collection_id')

    with op.batch_alter_table('access_requests', naming_convention=naming_convention, schema=None) as batch_op:
        batch_op.drop_constraint('fk_access_requests_collection_id_collections', type_='foreignkey')
        batch_op.drop_column('collection_id')

    with op.batch_alter_table('processes', naming_convention=naming_convention, schema=None) as batch_op:
        batch_op.add_column(sa.Column('collection_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_processes_collection_id_collections', 'collections', ['collection_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    naming_convention = {
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    }
    with op.batch_alter_table('processes', naming_convention=naming_convention, schema=None) as batch_op:
        batch_op.drop_constraint('fk_processes_collection_id_collections', type_='foreignkey')
        batch_op.drop_column('collection_id')

    with op.batch_alter_table('permissions', naming_convention=naming_convention, schema=None) as batch_op:
        batch_op.add_column(sa.Column('collection_id', sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key('fk_permissions_collection_id_collections', 'collections', ['collection_id'], ['id'])

    with op.batch_alter_table('direct_access', naming_convention=naming_convention, schema=None) as batch_op:
        batch_op.add_column(sa.Column('collection_id', sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key('fk_direct_access_collection_id_collections', 'collections', ['collection_id'], ['id'])

    with op.batch_alter_table('access_requests', naming_convention=naming_convention, schema=None) as batch_op:
        batch_op.add_column(sa.Column('collection_id', sa.INTEGER(), nullable=True))
        batch_op.create_foreign_key('fk_access_requests_collection_id_collections', 'collections', ['collection_id'], ['id'])

    # ### end Alembic commands ###
