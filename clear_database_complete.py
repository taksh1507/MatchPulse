#!/usr/bin/env python3
"""
Complete Database Clear - Remove all data and clear cache
"""

from dotenv import load_dotenv
import os
import shutil
import requests
import time

# Load environment variables
load_dotenv()

print("=== COMPLETE DATABASE CLEANUP SCRIPT ===")
print("This will remove ALL team registrations and clear cache!")
print("Are you sure you want to continue? (type 'YES' to confirm)")

confirmation = input("Confirmation: ")

if confirmation != 'YES':
    print("❌ Operation cancelled")
    exit()

def clear_database():
    """Clear the database"""
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
        
        return True
        
    except Exception as e:
        print(f"❌ Database cleanup failed: {e}")
        return False

def clear_files():
    """Clear QR codes and Excel files"""
    try:
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
            headers = ['Team ID', 'Player 1 Name', 'Player 1 PID', 'Player 2 Name', 'Player 2 PID', 
                      'Email', 'Payment Status', 'QR Code Path', 'Validation Status', 'Match Status', 
                      'Created At', 'Validated At']
            ws.append(headers)
            wb.save(excel_file)
            print("✅ Created new empty Excel backup file")
        else:
            print("ℹ️ Excel backup file not found")
        
        # Clear any cache files
        cache_files = ['cache.json', 'teams_cache.json', 'stats_cache.json', 'app_cache.json']
        for cache_file in cache_files:
            if os.path.exists(cache_file):
                os.remove(cache_file)
                print(f"✅ Deleted cache file: {cache_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ File cleanup failed: {e}")
        return False

def clear_app_cache():
    """Try to clear app cache via API if app is running"""
    try:
        # Try to hit a cache clearing endpoint if app is running
        ports = [5000, 8000, 3000]  # Common ports
        
        for port in ports:
            try:
                # Check if app is running on this port
                response = requests.get(f'http://localhost:{port}/', timeout=2)
                if response.status_code == 200:
                    print(f"📡 Found app running on port {port}")
                    
                    # Try to clear cache via API (if endpoint exists)
                    try:
                        cache_response = requests.post(f'http://localhost:{port}/api/clear-cache', timeout=5)
                        if cache_response.status_code == 200:
                            print("✅ App cache cleared via API")
                        else:
                            print("⚠️ Cache clearing endpoint not available")
                    except:
                        print("⚠️ Cache clearing endpoint not available")
                    
                    break
            except:
                continue
        else:
            print("ℹ️ App not running - cache will be cleared on next restart")
        
        return True
        
    except Exception as e:
        print(f"⚠️ Could not clear app cache: {e}")
        return True  # Not critical

def main():
    """Main cleanup function"""
    success = True
    
    print("\n🔄 Starting complete cleanup...")
    
    # Step 1: Clear database
    print("\n--- Step 1: Database Cleanup ---")
    if not clear_database():
        success = False
    
    # Step 2: Clear files
    print("\n--- Step 2: File Cleanup ---")
    if not clear_files():
        success = False
    
    # Step 3: Clear app cache
    print("\n--- Step 3: Cache Cleanup ---")
    clear_app_cache()
    
    if success:
        print("\n🎉 COMPLETE CLEANUP SUCCESSFUL!")
        print("\n📋 What was cleared:")
        print("   ✅ All team registrations from database")
        print("   ✅ All QR code images")
        print("   ✅ Excel backup file (recreated empty)")
        print("   ✅ Cache files")
        print("\n⚠️  IMPORTANT NEXT STEPS:")
        print("   1. RESTART the Flask application to clear memory cache")
        print("   2. Stop the app (Ctrl+C) and run: python app_ngrok_optimized.py")
        print("   3. Refresh your browser to see empty data")
        print("\n🚀 System is now completely reset and ready for new registrations!")
    else:
        print("\n❌ CLEANUP FAILED!")
        print("Please check the errors above and try again.")

if __name__ == "__main__":
    main()