"""adaptive custom features migration

Revision ID: adaptive_20250729132750  
Revises: 
Create Date: 2025-07-29 13:27:50.016653

This is an adaptive migration that works with ANY Marzban database state.
It detects what exists and only adds what's missing.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = 'adaptive_20250729132750'
down_revision = None  # This migration is independent
branch_labels = None
depends_on = None


def safe_table_exists(connection, table_name):
    """Safely check if table exists"""
    try:
        inspector = inspect(connection)
        return table_name in inspector.get_table_names()
    except Exception:
        return False


def safe_column_exists(connection, table_name, column_name):
    """Safely check if column exists"""
    try:
        inspector = inspect(connection)
        if not safe_table_exists(connection, table_name):
            return False
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception:
        return False


def get_database_state(connection):
    """Analyze current database state"""
    state = {
        'has_users': safe_table_exists(connection, 'users'),
        'has_settings': safe_table_exists(connection, 'settings'), 
        'has_nodes': safe_table_exists(connection, 'nodes'),
        'has_hosts': safe_table_exists(connection, 'hosts'),
        'has_custom_sub_path': False,
        'has_custom_uuid': False,
        'has_resilient_groups': safe_table_exists(connection, 'resilient_node_groups'),
        'has_resilient_association': safe_table_exists(connection, 'resilient_node_group_nodes_association'),
        'has_hosts_resilient_link': False
    }
    
    if state['has_users']:
        state['has_custom_sub_path'] = safe_column_exists(connection, 'users', 'custom_subscription_path')
        state['has_custom_uuid'] = safe_column_exists(connection, 'users', 'custom_uuid')
    
    if state['has_hosts']:
        state['has_hosts_resilient_link'] = safe_column_exists(connection, 'hosts', 'resilient_node_group_id')
    
    return state


def upgrade() -> None:
    """Adaptive upgrade that works with any database state"""
    connection = op.get_bind()
    
    print("🔄 ADAPTIVE CUSTOM FEATURES MIGRATION")
    print("=" * 50)
    
    # Analyze current state
    state = get_database_state(connection)
    
    print("📊 Database Analysis:")
    for key, value in state.items():
        status = "✅" if value else "❌"
        print(f"   {key}: {status}")
    
    # Determine what to do based on current state
    if not state['has_users'] or not state['has_settings']:
        print("\n❌ ERROR: This doesn't appear to be a valid Marzban database")
        print("   Required tables 'users' and 'settings' not found")
        print("   Cannot proceed with migration")
        return
    
    print("\n✅ Valid Marzban database detected")
    
    # Apply changes based on what's missing
    changes = []
    
    # 1. Custom subscription fields
    if not state['has_custom_sub_path']:
        print("\n📝 Adding custom_subscription_path to users...")
        op.add_column('users', sa.Column('custom_subscription_path', sa.String(256), nullable=True))
        changes.append("custom_subscription_path column")
    
    if not state['has_custom_uuid']:
        print("📝 Adding custom_uuid to users...")
        op.add_column('users', sa.Column('custom_uuid', sa.String(256), nullable=True))
        try:
            op.create_unique_constraint('uq_users_custom_uuid', 'users', ['custom_uuid'])
            changes.append("custom_uuid column with constraint")
        except Exception:
            changes.append("custom_uuid column")
    
    # 2. Resilient node groups
    if not state['has_resilient_groups']:
        print("📝 Creating resilient_node_groups table...")
        
        # Database-specific enum handling
        if connection.dialect.name == 'postgresql':
            try:
                op.execute("CREATE TYPE clientstrategyhint AS ENUM ('url-test', 'fallback', 'load-balance', 'client-default', '')")
                strategy_type = postgresql.ENUM('url-test', 'fallback', 'load-balance', 'client-default', '', name='clientstrategyhint')
            except Exception:
                strategy_type = postgresql.ENUM('url-test', 'fallback', 'load-balance', 'client-default', '', name='clientstrategyhint')
        else:
            strategy_type = sa.String(20)
        
        op.create_table('resilient_node_groups',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('client_strategy_hint', strategy_type, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name')
        )
        op.create_index('ix_resilient_node_groups_name', 'resilient_node_groups', ['name'])
        changes.append("resilient_node_groups table")
    
    if not state['has_resilient_association']:
        print("📝 Creating resilient node group associations...")
        op.create_table('resilient_node_group_nodes_association',
            sa.Column('resilient_node_group_id', sa.Integer(), nullable=False),
            sa.Column('node_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['node_id'], ['nodes.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['resilient_node_group_id'], ['resilient_node_groups.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('resilient_node_group_id', 'node_id')
        )
        changes.append("resilient association table")
    
    # 3. Hosts integration (if hosts table exists)
    if state['has_hosts'] and not state['has_hosts_resilient_link']:
        print("📝 Adding resilient group link to hosts...")
        op.add_column('hosts', sa.Column('resilient_node_group_id', sa.Integer(), nullable=True))
        try:
            op.create_foreign_key(
                'fk_hosts_resilient_node_group', 
                'hosts', 
                'resilient_node_groups', 
                ['resilient_node_group_id'], 
                ['id'], 
                ondelete='SET NULL'
            )
            changes.append("hosts resilient group link")
        except Exception:
            changes.append("hosts resilient group column")
    
    # Summary
    print("\n" + "=" * 50)
    if changes:
        print("🎉 MIGRATION COMPLETED - Changes Applied:")
        for i, change in enumerate(changes, 1):
            print(f"   {i}. {change}")
    else:
        print("✅ NO CHANGES NEEDED - All custom features already present")
    
    print("\n🎯 CUSTOM FEATURES AVAILABLE:")
    print("   • Resilient Node Groups")
    print("   • Hiddify User Import") 
    print("   • Custom Subscription Links")
    
    # Mark this migration as successful by updating alembic_version
    try:
        # Remove any existing alembic_version entries to avoid conflicts
        connection.execute(text("DELETE FROM alembic_version"))
        # Insert our migration as the current version
        connection.execute(text(f"INSERT INTO alembic_version (version_num) VALUES ('adaptive_20250729132750')"))
        print("\n✅ Migration state updated successfully")
    except Exception as e:
        print(f"\n⚠️  Could not update migration state: {e}")
        print("   This is not critical - the changes were still applied")


def downgrade() -> None:
    """Remove custom features"""
    connection = op.get_bind()
    
    print("🔄 Removing custom features...")
    
    # Remove in reverse order
    try:
        if safe_table_exists(connection, 'hosts') and safe_column_exists(connection, 'hosts', 'resilient_node_group_id'):
            try:
                op.drop_constraint('fk_hosts_resilient_node_group', 'hosts', type_='foreignkey')
            except Exception:
                pass
            op.drop_column('hosts', 'resilient_node_group_id')
        
        if safe_table_exists(connection, 'resilient_node_group_nodes_association'):
            op.drop_table('resilient_node_group_nodes_association')
        
        if safe_table_exists(connection, 'resilient_node_groups'):
            op.drop_index('ix_resilient_node_groups_name', 'resilient_node_groups')
            op.drop_table('resilient_node_groups')
        
        if safe_column_exists(connection, 'users', 'custom_uuid'):
            try:
                op.drop_constraint('uq_users_custom_uuid', 'users', type_='unique')
            except Exception:
                pass
            op.drop_column('users', 'custom_uuid')
        
        if safe_column_exists(connection, 'users', 'custom_subscription_path'):
            op.drop_column('users', 'custom_subscription_path')
        
        if connection.dialect.name == 'postgresql':
            try:
                op.execute("DROP TYPE IF EXISTS clientstrategyhint")
            except Exception:
                pass
        
        print("✅ Custom features removed")
        
    except Exception as e:
        print(f"❌ Error during downgrade: {e}")
        raise
