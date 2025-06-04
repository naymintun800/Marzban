"""add_load_balancer_debug_abs_path

Revision ID: c83bf33c0b66
Revises: add_custom_subscription_fields
Create Date: 2025-06-04 12:16:26.224481

"""
from alembic import op
import sqlalchemy as sa
from app.models.load_balancer import LoadBalancerStrategy # For Enum values
from app.models.proxy import ProxyHostSecurity, ProxyHostALPN, ProxyHostFingerprint # For Enum values


# revision identifiers, used by Alembic.
revision = 'c83bf33c0b66'
down_revision = 'add_custom_subscription_fields' # Make sure this is the actual previous migration's revision ID or symbolic name
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('load_balancer_hosts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=256, collation='NOCASE'), nullable=False),
        sa.Column('remark_template', sa.String(length=256), nullable=False, server_default="LB-{USERNAME}-{PROTOCOL}"),
        sa.Column('address', sa.String(length=256), nullable=False),
        sa.Column('port', sa.Integer(), nullable=True),
        sa.Column('path', sa.String(length=256), nullable=True),
        sa.Column('sni', sa.String(length=1000), nullable=True),
        sa.Column('host_header', sa.String(length=1000), nullable=True),
        sa.Column('security', sa.Enum(ProxyHostSecurity, name='proxyhostsecurity'), nullable=False, server_default=ProxyHostSecurity.inbound_default.name),
        sa.Column('alpn', sa.Enum(ProxyHostALPN, name='proxyhostalpn'), nullable=False, server_default=ProxyHostALPN.none.name),
        sa.Column('fingerprint', sa.Enum(ProxyHostFingerprint, name='proxyhostfingerprint'), nullable=False, server_default=ProxyHostFingerprint.none.name),
        sa.Column('allowinsecure', sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column('is_disabled', sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column('mux_enable', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('fragment_setting', sa.String(length=100), nullable=True),
        sa.Column('noise_setting', sa.String(length=2000), nullable=True),
        sa.Column('random_user_agent', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('use_sni_as_host', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('inbound_tag', sa.String(length=256), nullable=False),
        sa.Column('load_balancing_strategy', sa.Enum(LoadBalancerStrategy, name='loadbalancerstrategy'), nullable=False, server_default=LoadBalancerStrategy.ROUND_ROBIN.name),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['inbound_tag'], ['inbounds.tag'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='uq_lb_host_name'),
        sa.UniqueConstraint('address', 'port', 'inbound_tag', 'sni', name='_lb_host_uc')
    )
    op.create_index(op.f('ix_load_balancer_hosts_name'), 'load_balancer_hosts', ['name'], unique=True)

    op.create_table('loadbalancer_nodes_association',
        sa.Column('load_balancer_host_id', sa.Integer(), nullable=False),
        sa.Column('node_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['load_balancer_host_id'], ['load_balancer_hosts.id'], ),
        sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ),
        sa.PrimaryKeyConstraint('load_balancer_host_id', 'node_id')
    )


def downgrade() -> None:
    op.drop_table('loadbalancer_nodes_association')
    op.drop_index(op.f('ix_load_balancer_hosts_name'), table_name='load_balancer_hosts')
    op.drop_table('load_balancer_hosts')
    # Enum types for SQLite are typically handled by dropping the table.
    # For other databases like PostgreSQL, explicit DROP TYPE might be needed.
    # op.execute("DROP TYPE IF EXISTS loadbalancerstrategy;")
    # op.execute("DROP TYPE IF EXISTS proxyhostsecurity;")
    # op.execute("DROP TYPE IF EXISTS proxyhostalpn;")
    # op.execute("DROP TYPE IF EXISTS proxyhostfingerprint;")
    # However, to be safe and cover different SQLAlchemy versions/backends, explicit drop:
    bind = op.get_bind()
    if bind.dialect.name != 'sqlite': # Only attempt to drop types if not SQLite
        sa.Enum(LoadBalancerStrategy, name='loadbalancerstrategy').drop(bind, checkfirst=False)
        sa.Enum(ProxyHostSecurity, name='proxyhostsecurity').drop(bind, checkfirst=False)
        sa.Enum(ProxyHostALPN, name='proxyhostalpn').drop(bind, checkfirst=False)
        sa.Enum(ProxyHostFingerprint, name='proxyhostfingerprint').drop(bind, checkfirst=False) 