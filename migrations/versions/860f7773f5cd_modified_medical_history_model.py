"""modified medical history model

Revision ID: 860f7773f5cd
Revises: 0a4e72b3aa26
Create Date: 2025-01-27 17:37:53.578310

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '860f7773f5cd'
down_revision = '0a4e72b3aa26'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('medical_history', schema=None) as batch_op:
        batch_op.add_column(sa.Column('doctor_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_medical_history_doctor', 'doctor', ['doctor_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('medical_history', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('doctor_id')

    # ### end Alembic commands ###
