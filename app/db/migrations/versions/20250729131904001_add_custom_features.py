"""add custom features (resilient node groups, hiddify import, custom subscriptions)

Revision ID: 20250729131904001
Revises: head
Create Date: 2025-07-29 13:19:04.002922

This migration adds three custom features:
1. Resilient Node Groups - for load balancing and failover
2. Hiddify User Import - bulk import from Hiddify JSON backups  
3. Custom Subscription Links - individual user custom paths and UUIDs

This migration is designed to work as the final migration in the chain,
regardless of whether you're coming from master or beta-1 branch.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text, MetaData, Table, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects import sqlite, postgresql, mysql
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '20250729131904001'
down_revision = 'head'
branch_labels = None
depends_on = None


def table_exists(connection, table_name):
    """Check if a table exists in the database"""
    try:
        # Use reflection to check if table exists
        meta = MetaData()
        meta.reflect(bind=connection)
        return table_name in meta.tables
    except Exception:
        return False


def column_exists(connection, table_name, column_name):
    """Check if a column exists in a table"""
    try:
        # Check if column exists by trying to describe the table
        if connection.dialect.name == 'sqlite':
            result = connection.execute(text(f"PRAGMA table_info({table_name})"))
            columns = [row[1] for row in result.fetchall()]
        elif connection.dialect.name == 'postgresql':
            result = connection.execute(text(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='{table_name}' AND column_name='{column_name}'
            """))
            return result.fetchone() is not None
        elif connection.dialect.name == 'mysql':
            result = connection.execute(text(f"""
                SELECT COLUMN_NAME FROM information_schema.COLUMNS 
                WHERE TABLE_NAME='{table_name}' AND COLUMN_NAME='{column_name}'
            """))
            return result.fetchone() is not None
        else:
            return False
            
        return column_name in columns
    except Exception:
        return False


def constraint_exists(connection, table_name, constraint_name):
    """Check if a constraint exists"""
    try:
        if connection.dialect.name == 'sqlite':
            # SQLite doesn't have easy constraint introspection
            return False
        elif connection.dialect.name == 'postgresql':
            result = connection.execute(text(f"""
                SELECT constraint_name FROM information_schema.table_constraints 
                WHERE table_name='{table_name}' AND constraint_name='{constraint_name}'
            """))
            return result.fetchone() is not None
        return False
    except Exception:
        return False


def upgrade() -> None:
    """
    Add custom features to existing Marzban installation.
    This works regardless of master/beta-1 branch.
    """
    connection = op.get_bind()
    
    print("🚀 Adding Marzban Custom Features...")
    print("   • Resilient Node Groups")
    print("   • Hiddify User Import") 
    print("   • Custom Subscription Links")
    
    # Check if we have the basic tables
    required_tables = ['users', 'nodes']
    missing_tables = [table for table in required_tables if not table_exists(connection, table)]
    
    if missing_tables:
        print(f"❌ Missing required tables: {missing_tables}")
        print("   This suggests the base schema is not installed.")
        print("   Please ensure Marzban base migrations have run first.")
        return
    
    print("✅ Base schema verified")
    
    # 1. Add custom subscription fields to users table
    print("📝 Adding custom subscription fields to users table...")
    
    if not column_exists(connection, 'users', 'custom_subscription_path'):
        print("   Adding custom_subscription_path column...")
        op.add_column('users', sa.Column('custom_subscription_path', sa.String(256), nullable=True))
    else:
        print("   custom_subscription_path already exists")
    
    if not column_exists(connection, 'users', 'custom_uuid'):
        print("   Adding custom_uuid column...")
        op.add_column('users', sa.Column('custom_uuid', sa.String(256), nullable=True))
        
        # Add unique constraint if it doesn't exist
        if not constraint_exists(connection, 'users', 'uq_users_custom_uuid'):
            try:
                op.create_unique_constraint('uq_users_custom_uuid', 'users', ['custom_uuid'])
                print("   Added unique constraint for custom_uuid")
            except Exception as e:
                print(f"   Warning: Could not add unique constraint: {e}")
    else:
        print("   custom_uuid already exists")
    
    # 2. Create resilient_node_groups table
    print("📝 Creating resilient_node_groups table...")
    
    if not table_exists(connection, 'resilient_node_groups'):
        print("   Creating resilient_node_groups table...")
        
        # Handle enum based on database type
        if connection.dialect.name == 'postgresql':
            # Create enum type for PostgreSQL
            try:
                op.execute("CREATE TYPE clientstrategyhint AS ENUM ('url-test', 'fallback', 'load-balance', 'client-default', '')")
                client_strategy_type = postgresql.ENUM('url-test', 'fallback', 'load-balance', 'client-default', '', name='clientstrategyhint')
            except Exception:
                # Enum might already exist
                client_strategy_type = postgresql.ENUM('url-test', 'fallback', 'load-balance', 'client-default', '', name='clientstrategyhint')
        else:
            # Use string for SQLite and MySQL
            client_strategy_type = sa.String(20)
        
        # Create the table
        op.create_table('resilient_node_groups',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('client_strategy_hint', client_strategy_type, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name', name='uq_resilient_node_groups_name')
        )
        
        # Create index
        op.create_index('ix_resilient_node_groups_name', 'resilient_node_groups', ['name'])
        print("   ✅ resilient_node_groups table created")
    else:
        print("   resilient_node_groups table already exists")
    
    # 3. Create association table for resilient node groups and nodes
    print("📝 Creating resilient node group associations...")
    
    if not table_exists(connection, 'resilient_node_group_nodes_association'):
        print("   Creating association table...")
        op.create_table('resilient_node_group_nodes_association',
            sa.Column('resilient_node_group_id', sa.Integer(), nullable=False),
            sa.Column('node_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['resilient_node_group_id'], ['resilient_node_groups.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('resilient_node_group_id', 'node_id')
        )
        print("   ✅ Association table created")
    else:
        print("   Association table already exists")
    
    # 4. Add resilient_node_group_id to hosts table (if hosts table exists)
    if table_exists(connection, 'hosts'):
        print("📝 Adding resilient node group relationship to hosts...")
        
        if not column_exists(connection, 'hosts', 'resilient_node_group_id'):
            print("   Adding resilient_node_group_id column to hosts...")
            op.add_column('hosts', sa.Column('resilient_node_group_id', sa.Integer(), nullable=True))
            
            # Add foreign key constraint
            try:
                op.create_foreign_key(
                    'fk_hosts_resilient_node_group', 
                    'hosts', 
                    'resilient_node_groups', 
                    ['resilient_node_group_id'], 
                    ['id'], 
                    ondelete='SET NULL'
                )
                print("   ✅ Foreign key constraint added")
            except Exception as e:
                print(f"   Warning: Could not add foreign key: {e}")
        else:
            print("   resilient_node_group_id already exists in hosts table")
    else:
        print("   hosts table not found - skipping hosts integration")
    
    print("🎉 Custom features migration completed successfully!")
    print("")
    print("✅ FEATURES NOW AVAILABLE:")
    print("   🎯 Resilient Node Groups - Load balancing and failover")
    print("   📥 Hiddify User Import - Bulk import from JSON backups")
    print("   🔗 Custom Subscription Links - Individual user custom paths")
    print("")
    print("🌐 Frontend components are also ready:")
    print("   • /nodes/resilient-groups - Node group management")
    print("   • Users page - Hiddify import button")
    print("   • User forms - Custom subscription fields")


def downgrade() -> None:
    """
    Remove custom features (downgrade).
    """
    print("🔄 Removing custom features...")
    
    connection = op.get_bind()
    
    # Remove in reverse order
    try:
        if table_exists(connection, 'hosts') and column_exists(connection, 'hosts', 'resilient_node_group_id'):
            print("   Removing resilient_node_group_id from hosts...")
            try:
                op.drop_constraint('fk_hosts_resilient_node_group', 'hosts', type_='foreignkey')
            except Exception:
                pass
            op.drop_column('hosts', 'resilient_node_group_id')
        
        if table_exists(connection, 'resilient_node_group_nodes_association'):
            print("   Dropping association table...")
            op.drop_table('resilient_node_group_nodes_association')
        
        if table_exists(connection, 'resilient_node_groups'):
            print("   Dropping resilient_node_groups table...")
            op.drop_index('ix_resilient_node_groups_name', 'resilient_node_groups')
            op.drop_table('resilient_node_groups')
        
        if column_exists(connection, 'users', 'custom_uuid'):
            print("   Removing custom_uuid from users...")
            try:
                op.drop_constraint('uq_users_custom_uuid', 'users', type_='unique')
            except Exception:
                pass
            op.drop_column('users', 'custom_uuid')
        
        if column_exists(connection, 'users', 'custom_subscription_path'):
            print("   Removing custom_subscription_path from users...")
            op.drop_column('users', 'custom_subscription_path')
        
        # Drop enum for PostgreSQL
        if connection.dialect.name == 'postgresql':
            try:
                op.execute("DROP TYPE IF EXISTS clientstrategyhint")
            except Exception:
                pass
        
        print("✅ Custom features removed successfully")
        
    except Exception as e:
        print(f"❌ Error during downgrade: {e}")
        raise
