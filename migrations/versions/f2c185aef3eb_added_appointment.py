"""Added appointment

Revision ID: f2c185aef3eb
Revises: e8bf53e8097b
Create Date: 2024-12-27 17:20:59.577769

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2c185aef3eb'
down_revision = 'e8bf53e8097b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('appointment',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('appointment_time', sa.String(length=100), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('doctor_id', sa.Integer(), nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['client_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['doctor_id'], ['doctor.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('appointment')
    # ### end Alembic commands ###
