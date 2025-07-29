"""branch agnostic custom features migration

Revision ID: 99999999
Revises: 
Create Date: 2025-07-28 23:00:00.000000

This migration is designed to work with both master and beta-1 branches.
It detects the current schema state and applies only the necessary changes.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text, inspect
from sqlalchemy.dialects import sqlite, postgresql, mysql


# revision identifiers, used by Alembic.
revision = '20250729000054'
down_revision = '94a5cc12c0d6'  # init_user_table - exists in both master and beta-1
branch_labels = None
depends_on = None


def get_current_head_revision():
    """Dynamically determine the current head revision"""
    connection = op.get_bind()
    
    try:
        # Check if alembic_version table exists
        result = connection.execute(text(
            "SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1"
        ))
        current_revision = result.scalar()
        return current_revision
    except Exception:
        # If no alembic_version table, we're starting fresh
        return None


def table_exists(connection, table_name):
    """Check if a table exists"""
    inspector = inspect(connection)
    return table_name in inspector.get_table_names()


def column_exists(connection, table_name, column_name):
    """Check if a column exists in a table"""
    try:
        inspector = inspect(connection)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def upgrade() -> None:
    """
    Branch-agnostic upgrade that works with both master and beta-1 branches.
    Detects current schema state and applies only necessary changes.
    """
    connection = op.get_bind()
    
    print("🔄 Starting branch-agnostic custom features migration...")
    
    # Check current schema state
    if not table_exists(connection, 'users'):
        print("❌ Users table not found. Base schema must be created first.")
        raise Exception("Base schema not found. Run base migrations first.")
    
    # 1. Add custom subscription fields to users table if they don't exist
    print("📝 Checking custom subscription fields...")
    
    if not column_exists(connection, 'users', 'custom_subscription_path'):
        print("   Adding custom_subscription_path column...")
        op.add_column('users', sa.Column('custom_subscription_path', sa.String(256), nullable=True))
    else:
        print("   custom_subscription_path column already exists")
    
    if not column_exists(connection, 'users', 'custom_uuid'):
        print("   Adding custom_uuid column...")
        op.add_column('users', sa.Column('custom_uuid', sa.String(256), nullable=True))
        
        # Add unique constraint
        try:
            op.create_unique_constraint('uq_users_custom_uuid', 'users', ['custom_uuid'])
        except Exception as e:
            print(f"   Warning: Could not create unique constraint: {e}")
    else:
        print("   custom_uuid column already exists")
    
    # 2. Create resilient_node_groups table if it doesn't exist
    print("📝 Checking resilient node groups table...")
    
    if not table_exists(connection, 'resilient_node_groups'):
        print("   Creating resilient_node_groups table...")
        
        # Create ClientStrategyHint enum
        if connection.dialect.name == 'postgresql':
            op.execute("CREATE TYPE clientstrategyhint AS ENUM ('url-test', 'fallback', 'load-balance', 'client-default', '')")
            client_strategy_type = postgresql.ENUM('url-test', 'fallback', 'load-balance', 'client-default', '', name='clientstrategyhint')
        else:
            client_strategy_type = sa.String(20)
        
        op.create_table('resilient_node_groups',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('client_strategy_hint', client_strategy_type, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        op.create_index('ix_resilient_node_groups_name', 'resilient_node_groups', ['name'])
    else:
        print("   resilient_node_groups table already exists")
    
    # 3. Create association table for resilient node groups and nodes
    print("📝 Checking resilient node group associations...")
    
    if not table_exists(connection, 'resilient_node_group_nodes_association'):
        print("   Creating resilient_node_group_nodes_association table...")
        op.create_table('resilient_node_group_nodes_association',
            sa.Column('resilient_node_group_id', sa.Integer(), nullable=False),
            sa.Column('node_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ),
            sa.ForeignKeyConstraint(['resilient_node_group_id'], ['resilient_node_groups.id'], ),
            sa.PrimaryKeyConstraint('resilient_node_group_id', 'node_id')
        )
    else:
        print("   resilient_node_group_nodes_association table already exists")
    
    # 4. Add resilient_node_group_id to hosts table if it doesn't exist
    print("📝 Checking hosts table resilient node group relationship...")
    
    if table_exists(connection, 'hosts') and not column_exists(connection, 'hosts', 'resilient_node_group_id'):
        print("   Adding resilient_node_group_id to hosts table...")
        op.add_column('hosts', sa.Column('resilient_node_group_id', sa.Integer(), nullable=True))
        
        try:
            op.create_foreign_key('fk_hosts_resilient_node_group', 'hosts', 'resilient_node_groups', ['resilient_node_group_id'], ['id'], ondelete='SET NULL')
        except Exception as e:
            print(f"   Warning: Could not create foreign key: {e}")
    else:
        print("   resilient_node_group_id column already exists or hosts table not found")
    
    print("✅ Branch-agnostic custom features migration completed successfully!")
    print("🎉 Custom features are now available:")
    print("   • Resilient Node Groups")
    print("   • Hiddify User Import (backend API)")
    print("   • Custom Subscription Links")


def downgrade() -> None:
    """
    Downgrade custom features.
    """
    print("🔄 Downgrading custom features...")
    
    connection = op.get_bind()
    
    # Remove columns and tables in reverse order
    if column_exists(connection, 'hosts', 'resilient_node_group_id'):
        op.drop_constraint('fk_hosts_resilient_node_group', 'hosts', type_='foreignkey')
        op.drop_column('hosts', 'resilient_node_group_id')
    
    if table_exists(connection, 'resilient_node_group_nodes_association'):
        op.drop_table('resilient_node_group_nodes_association')
    
    if table_exists(connection, 'resilient_node_groups'):
        op.drop_index('ix_resilient_node_groups_name', 'resilient_node_groups')
        op.drop_table('resilient_node_groups')
    
    if column_exists(connection, 'users', 'custom_uuid'):
        op.drop_constraint('uq_users_custom_uuid', 'users', type_='unique')
        op.drop_column('users', 'custom_uuid')
    
    if column_exists(connection, 'users', 'custom_subscription_path'):
        op.drop_column('users', 'custom_subscription_path')
    
    # Drop enum if PostgreSQL
    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        op.execute("DROP TYPE IF EXISTS clientstrategyhint")
    
    print("✅ Custom features downgrade completed")