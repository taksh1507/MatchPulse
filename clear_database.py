#!/usr/bin/env python3
"""
Clear database - Remove all team registrations
"""

from dotenv import load_dotenv
import os
import shutil

# Load environment variables
load_dotenv()

print("=== Database Cleanup Script ===")
print("This will remove ALL team registrations!")
print("Are you sure you want to continue? (type 'YES' to confirm)")

confirmation = input("Confirmation: ")

if confirmation != 'YES':
    print("❌ Operation cancelled")
    exit()

try:
    import psycopg2
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    USE_POSTGRES = DATABASE_URL and DATABASE_URL.startswith('postgresql://')
    
    if USE_POSTGRES:
        print("🗄️ Clearing PostgreSQL database...")
        
        # Handle Neon database URL with channel_binding parameter
        db_url = DATABASE_URL
        if 'channel_binding=require' in db_url:
            db_url = db_url.replace('&channel_binding=require', '').replace('?channel_binding=require&', '?').replace('?channel_binding=require', '')
        
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Clear all teams
        cur.execute("DELETE FROM teams")
        rows_deleted = cur.rowcount
        
        # Reset any auto-increment sequences if they exist
        try:
            cur.execute("ALTER SEQUENCE teams_id_seq RESTART WITH 1")
        except:
            pass  # Sequence might not exist
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Deleted {rows_deleted} teams from PostgreSQL database")
        
    else:
        print("🗄️ Clearing SQLite database...")
        
        import sqlite3
        db_path = DATABASE_URL.replace('sqlite:///', '') if DATABASE_URL else 'teams.db'
        
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            
            # Clear all teams
            cur.execute("DELETE FROM teams")
            rows_deleted = cur.rowcount
            
            # Reset auto-increment
            cur.execute("DELETE FROM sqlite_sequence WHERE name='teams'")
            
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"✅ Deleted {rows_deleted} teams from SQLite database")
        else:
            print("ℹ️ SQLite database file not found")
    
    # Clear QR code images
    qr_dir = 'static/qr_codes'
    if os.path.exists(qr_dir):
        qr_files = [f for f in os.listdir(qr_dir) if f.endswith('.png')]
        for qr_file in qr_files:
            os.remove(os.path.join(qr_dir, qr_file))
        print(f"✅ Deleted {len(qr_files)} QR code images")
    else:
        print("ℹ️ QR codes directory not found")
    
    # Clear Excel backup
    excel_file = 'teams_backup.xlsx'
    if os.path.exists(excel_file):
        os.remove(excel_file)
        print("✅ Deleted Excel backup file")
        
        # Recreate empty Excel file
        import openpyxl
        from openpyxl import Workbook
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Teams"
        headers = ['Team ID', 'Player 1 Name', 'Player 2 Name', 'Email', 'Payment Status', 
                  'QR Code Path', 'Validation Status', 'Match Status', 'Created At', 'Validated At']
        ws.append(headers)
        wb.save(excel_file)
        print("✅ Created new empty Excel backup file")
    else:
        print("ℹ️ Excel backup file not found")
    
    print("\n🎉 Database cleanup completed successfully!")
    print("The system is now reset and ready for new registrations.")
    
except Exception as e:
    print(f"❌ Database cleanup failed: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure the database is accessible")
    print("2. Check your .env file configuration")
    print("3. Ensure no other processes are using the database")