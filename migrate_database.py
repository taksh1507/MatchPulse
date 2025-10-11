#!/usr/bin/env python3
"""
Database Migration Script - Add PID columns to existing database
"""

from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

print("=== Database Migration Script ===")
print("Adding PID and Goal Time columns to existing teams table...")

try:
    import psycopg2
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    USE_POSTGRES = DATABASE_URL and DATABASE_URL.startswith('postgresql://')
    
    if USE_POSTGRES:
        print("🗄️ Migrating PostgreSQL database...")
        
        # Handle Neon database URL with channel_binding parameter
        db_url = DATABASE_URL
        if 'channel_binding=require' in db_url:
            db_url = db_url.replace('&channel_binding=require', '').replace('?channel_binding=require&', '?').replace('?channel_binding=require', '')
        
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Check if columns exist
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'teams' AND column_name IN ('player1_pid', 'player2_pid', 'player1_phone', 'player2_phone', 'goal_time', 'goal_recorded_at')
        """)
        existing_columns = [row[0] for row in cur.fetchall()]
        
        # Add missing PID columns
        if 'player1_pid' not in existing_columns:
            cur.execute('ALTER TABLE teams ADD COLUMN player1_pid VARCHAR(20)')
            print("✅ Added player1_pid column")
        else:
            print("ℹ️ player1_pid column already exists")
        
        if 'player2_pid' not in existing_columns:
            cur.execute('ALTER TABLE teams ADD COLUMN player2_pid VARCHAR(20)')
            print("✅ Added player2_pid column")
        else:
            print("ℹ️ player2_pid column already exists")
        
        # Add missing Phone columns
        if 'player1_phone' not in existing_columns:
            cur.execute('ALTER TABLE teams ADD COLUMN player1_phone VARCHAR(20)')
            print("✅ Added player1_phone column")
        else:
            print("ℹ️ player1_phone column already exists")
        
        if 'player2_phone' not in existing_columns:
            cur.execute('ALTER TABLE teams ADD COLUMN player2_phone VARCHAR(20)')
            print("✅ Added player2_phone column")
        else:
            print("ℹ️ player2_phone column already exists")
        
        # Add missing Goal Time columns
        if 'goal_time' not in existing_columns:
            cur.execute('ALTER TABLE teams ADD COLUMN goal_time DECIMAL(8,3)')
            print("✅ Added goal_time column")
        else:
            print("ℹ️ goal_time column already exists")
        
        if 'goal_recorded_at' not in existing_columns:
            cur.execute('ALTER TABLE teams ADD COLUMN goal_recorded_at TIMESTAMP')
            print("✅ Added goal_recorded_at column")
        else:
            print("ℹ️ goal_recorded_at column already exists")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("✅ PostgreSQL migration completed successfully!")
        
    else:
        print("🗄️ Migrating SQLite database...")
        
        import sqlite3
        db_path = DATABASE_URL.replace('sqlite:///', '') if DATABASE_URL else 'teams.db'
        
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            
            # Check if columns exist
            cur.execute("PRAGMA table_info(teams)")
            columns = [row[1] for row in cur.fetchall()]
            
            # Add missing PID columns
            if 'player1_pid' not in columns:
                cur.execute('ALTER TABLE teams ADD COLUMN player1_pid TEXT')
                print("✅ Added player1_pid column")
            else:
                print("ℹ️ player1_pid column already exists")
            
            if 'player2_pid' not in columns:
                cur.execute('ALTER TABLE teams ADD COLUMN player2_pid TEXT')
                print("✅ Added player2_pid column")
            else:
                print("ℹ️ player2_pid column already exists")
            
            # Add missing Phone columns
            if 'player1_phone' not in columns:
                cur.execute('ALTER TABLE teams ADD COLUMN player1_phone TEXT')
                print("✅ Added player1_phone column")
            else:
                print("ℹ️ player1_phone column already exists")
            
            if 'player2_phone' not in columns:
                cur.execute('ALTER TABLE teams ADD COLUMN player2_phone TEXT')
                print("✅ Added player2_phone column")
            else:
                print("ℹ️ player2_phone column already exists")
            
            # Add missing Goal Time columns
            if 'goal_time' not in columns:
                cur.execute('ALTER TABLE teams ADD COLUMN goal_time REAL')
                print("✅ Added goal_time column")
            else:
                print("ℹ️ goal_time column already exists")
            
            if 'goal_recorded_at' not in columns:
                cur.execute('ALTER TABLE teams ADD COLUMN goal_recorded_at DATETIME')
                print("✅ Added goal_recorded_at column")
            else:
                print("ℹ️ goal_recorded_at column already exists")
            
            conn.commit()
            cur.close()
            conn.close()
            
            print("✅ SQLite migration completed successfully!")
        else:
            print("❌ SQLite database file not found")
    
    print("\n🎉 Database migration completed!")
    print("You can now use:")
    print("  ✅ PID fields in team registration")
    print("  ✅ Phone numbers for winner identification")
    print("  ✅ Goal time recording in monitor dashboard")
    print("  ✅ Leaderboard with best times and contact info")
    
except Exception as e:
    print(f"❌ Migration failed: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure the database is accessible")
    print("2. Check your .env file configuration")
    print("3. Ensure no other processes are using the database")
    print("4. Try running the app - it will auto-migrate on startup")