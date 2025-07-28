#!/usr/bin/env python3
"""
Professional solution for upgrading from Marzban master to beta-1 with custom features.
This handles the migration path for production environments with existing data.
"""

import os
import subprocess
import sys

def run_docker_command(cmd, description):
    """Run a command in the Marzban container"""
    print(f"🔧 {description}")
    full_cmd = f"docker-compose exec -T marzban {cmd}"
    print(f"   Running: {full_cmd}")
    
    try:
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"   ✅ Success")
            return result.stdout.strip()
        else:
            print(f"   ❌ Failed: {result.stderr.strip()}")
            return None
    except subprocess.TimeoutExpired:
        print(f"   ⏰ Command timed out")
        return None
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return None

def main():
    print("🚀 Marzban Master → Beta-1 Migration Tool")
    print("=" * 50)
    print("This tool handles upgrading production Marzban from master to beta-1")
    print("with custom features while preserving existing data.")
    print()
    
    # Check if docker-compose is available
    if not os.system("docker-compose ps > /dev/null 2>&1") == 0:
        print("❌ Docker Compose not found or Marzban not running.")
        print("Please ensure Marzban is running with docker-compose.")
        sys.exit(1)
    
    print("📋 Step 1: Check current migration state")
    current_revision = run_docker_command("alembic current", "Get current migration revision")
    
    if current_revision:
        print(f"   Current revision: {current_revision}")
    else:
        print("   Could not determine current revision")
        print("   This might indicate:")
        print("   • Database is not initialized")
        print("   • Migration table doesn't exist")
        print("   • Connection issues")
        
        choice = input("\n   Continue anyway? (y/N): ").lower()
        if choice != 'y':
            print("Aborted.")
            sys.exit(1)
    
    print("\n📋 Step 2: Check available migrations")
    heads = run_docker_command("alembic heads", "Get migration heads")
    
    if heads:
        print(f"   Available heads: {heads}")
        if "multiple" in heads.lower():
            print("   ⚠️  Multiple heads detected - this is the issue we're fixing")
    
    print("\n📋 Step 3: Check migration history")
    history = run_docker_command("alembic history --verbose", "Get migration history")
    
    print("\n🔧 Fix Options:")
    print("1. Stamp to latest and let Alembic resolve (recommended for most cases)")
    print("2. Stamp to a specific revision manually")
    print("3. Show detailed migration analysis")
    print("4. Reset migration state and start fresh (⚠️  advanced)")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        print("\n🎯 Stamping to resolve migration conflicts...")
        
        # First, try to stamp to the branch-agnostic migration
        stamp_result = run_docker_command(
            "alembic stamp 20250729000054", 
            "Stamp to branch-agnostic custom features migration"
        )
        
        if stamp_result is not None:
            print("✅ Successfully stamped to custom features migration!")
            print("\n🔄 Now upgrading to ensure all migrations are applied...")
            
            upgrade_result = run_docker_command("alembic upgrade head", "Upgrade to head")
            
            if upgrade_result is not None:
                print("✅ Migration completed successfully!")
                print("\n🎉 Your custom features are now available:")
                print("   • Resilient Node Groups")
                print("   • Hiddify User Import")
                print("   • Custom Subscription Links")
            else:
                print("❌ Upgrade failed. Check logs above.")
        else:
            print("❌ Stamp failed. Try option 2 for manual approach.")
    
    elif choice == "2":
        print("\n📝 Manual revision stamping")
        revision = input("Enter the revision ID to stamp to: ").strip()
        
        if revision:
            stamp_result = run_docker_command(f"alembic stamp {revision}", f"Stamp to {revision}")
            if stamp_result is not None:
                print("✅ Successfully stamped!")
                upgrade = input("Upgrade to head now? (y/N): ").lower()
                if upgrade == 'y':
                    run_docker_command("alembic upgrade head", "Upgrade to head")
    
    elif choice == "3":
        print("\n📊 Detailed Migration Analysis")
        print("Current state:")
        if current_revision:
            print(f"   Current revision: {current_revision}")
        
        print("\nAll migration heads:")
        run_docker_command("alembic heads", "List all heads")
        
        print("\nMigration branches:")
        run_docker_command("alembic branches", "Show branches")
        
        print("\nRecent migration history:")
        run_docker_command("alembic history -r-10:", "Show last 10 migrations")
        
    elif choice == "4":
        print("\n⚠️  ADVANCED: Reset migration state")
        print("This will reset the migration tracking but keep your data.")
        print("Only use this if you understand the implications.")
        
        confirm = input("Type 'RESET' to confirm: ")
        if confirm == "RESET":
            # Drop and recreate alembic_version table
            print("Resetting migration state...")
            
            # This is dangerous but sometimes necessary
            reset_cmd = """python -c "
from alembic import command
from alembic.config import Config
from app.db import get_db, engine
from sqlalchemy import text

# Drop alembic version table
with engine.begin() as conn:
    conn.execute(text('DROP TABLE IF EXISTS alembic_version'))
    conn.execute(text('CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))'))

print('Migration state reset')
" """
            
            reset_result = run_docker_command(reset_cmd, "Reset migration state")
            
            if reset_result is not None:
                print("✅ Migration state reset")
                print("Now stamping to custom features migration...")
                run_docker_command("alembic stamp 20250729000054", "Stamp to custom features")
        else:
            print("Reset cancelled.")
    
    else:
        print("Invalid choice.")
    
    print("\n" + "=" * 50)
    print("🏁 Migration process completed!")
    print("Restart your Marzban container to see the changes:")
    print("   docker-compose restart marzban")
    print("   docker-compose logs -f marzban")

if __name__ == "__main__":
    main()