#!/usr/bin/env python3
"""
Master → Beta-1 Database Migration Tool
Handles the async/sync database driver transition properly.
"""

import sqlite3
import os
import shutil
import json
from datetime import datetime

def backup_database(db_path):
    """Create a backup of the existing database"""
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return None
    
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"✅ Database backed up to: {backup_path}")
    return backup_path

def analyze_database(db_path):
    """Analyze the current database structure"""
    if not os.path.exists(db_path):
        return None
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Check for Marzban-specific tables
        required_tables = ['users', 'admins', 'settings']
        has_required = all(table in tables for table in required_tables)
        
        # Check migration state
        migration_version = None
        if 'alembic_version' in tables:
            cursor.execute("SELECT version_num FROM alembic_version")
            result = cursor.fetchone()
            if result:
                migration_version = result[0]
        
        # Get user count
        user_count = 0
        if 'users' in tables:
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
        
        analysis = {
            'tables': tables,
            'has_required_tables': has_required,
            'migration_version': migration_version,
            'user_count': user_count,
            'is_marzban_db': has_required
        }
        
        return analysis
    
    finally:
        conn.close()

def prepare_for_beta1(db_path):
    """Prepare database for beta-1 compatibility"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔧 Preparing database for beta-1...")
        
        # Clear alembic version to allow fresh migration
        cursor.execute("DELETE FROM alembic_version")
        
        # Add custom features columns if they don't exist
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN custom_subscription_path TEXT")
            print("   ✅ Added custom_subscription_path column")
        except sqlite3.OperationalError:
            print("   ℹ️  custom_subscription_path already exists")
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN custom_uuid TEXT")
            print("   ✅ Added custom_uuid column")
        except sqlite3.OperationalError:
            print("   ℹ️  custom_uuid already exists")
        
        # Create resilient node groups table
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resilient_node_groups (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    client_strategy_hint TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("   ✅ Created resilient_node_groups table")
        except sqlite3.OperationalError as e:
            print(f"   ⚠️  Could not create resilient_node_groups: {e}")
        
        # Create association table
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS resilient_node_group_nodes_association (
                    resilient_node_group_id INTEGER,
                    node_id INTEGER,
                    PRIMARY KEY (resilient_node_group_id, node_id),
                    FOREIGN KEY (resilient_node_group_id) REFERENCES resilient_node_groups(id) ON DELETE CASCADE,
                    FOREIGN KEY (node_id) REFERENCES nodes(id) ON DELETE CASCADE
                )
            """)
            print("   ✅ Created association table")
        except sqlite3.OperationalError as e:
            print(f"   ⚠️  Could not create association table: {e}")
        
        # Add resilient group link to hosts if hosts table exists
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hosts'")
            if cursor.fetchone():
                try:
                    cursor.execute("ALTER TABLE hosts ADD COLUMN resilient_node_group_id INTEGER")
                    print("   ✅ Added resilient_node_group_id to hosts")
                except sqlite3.OperationalError:
                    print("   ℹ️  resilient_node_group_id already exists in hosts")
        except Exception as e:
            print(f"   ⚠️  Could not update hosts table: {e}")
        
        conn.commit()
        print("✅ Database prepared for beta-1")
        
    finally:
        conn.close()

def create_env_file():
    """Create a proper .env file for beta-1"""
    env_content = """# Marzban Beta-1 Configuration
SQLALCHEMY_DATABASE_URL=sqlite+aiosqlite:////var/lib/marzban/db.sqlite3

# Optional: Other configurations
# UVICORN_HOST=0.0.0.0
# UVICORN_PORT=8000
# DEBUG=False
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Created .env file with correct database URL")

def main():
    print("🚀 MARZBAN MASTER → BETA-1 MIGRATION TOOL")
    print("=" * 50)
    print("This tool helps migrate from master branch to beta-1 branch")
    print("with proper database driver compatibility.")
    print()
    
    # Database path
    db_paths = [
        "/var/lib/marzban/db.sqlite3",
        "./db.sqlite3",
        "./marzban.db",
        "./data/db.sqlite3"
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ No database found in common locations:")
        for path in db_paths:
            print(f"   - {path}")
        print("\nPlease specify the correct database path manually.")
        return False
    
    print(f"📁 Found database: {db_path}")
    
    # Analyze current database
    print("\n📊 Analyzing current database...")
    analysis = analyze_database(db_path)
    
    if not analysis:
        print("❌ Could not analyze database")
        return False
    
    if not analysis['is_marzban_db']:
        print("❌ This doesn't appear to be a valid Marzban database")
        print(f"   Missing required tables from: {['users', 'admins', 'settings']}")
        return False
    
    print("✅ Valid Marzban database detected")
    print(f"   Tables: {len(analysis['tables'])}")
    print(f"   Users: {analysis['user_count']}")
    print(f"   Migration version: {analysis['migration_version'] or 'None'}")
    
    # Create backup
    print("\n💾 Creating backup...")
    backup_path = backup_database(db_path)
    if not backup_path:
        print("❌ Could not create backup")
        return False
    
    # Prepare database
    print("\n🔧 Preparing database for beta-1...")
    try:
        prepare_for_beta1(db_path)
    except Exception as e:
        print(f"❌ Error preparing database: {e}")
        print(f"💾 Restore from backup: {backup_path}")
        return False
    
    # Create .env file
    print("\n📝 Creating configuration...")
    create_env_file()
    
    print("\n" + "=" * 50)
    print("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    print("📋 What was done:")
    print("   ✅ Database backed up")
    print("   ✅ Custom features schema added")
    print("   ✅ Migration state cleared")
    print("   ✅ .env file created with correct database URL")
    print()
    print("🚀 Next steps:")
    print("   1. Start your beta-1 Marzban container")
    print("   2. The database will work with async drivers")
    print("   3. Custom features will be available immediately")
    print()
    print("💾 Backup location:")
    print(f"   {backup_path}")
    print("   (Keep this safe for rollback if needed)")
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)