#!/usr/bin/env python3
"""
MatchPulse - Ngrok Optimized Version
Based on app_minimal_working.py with ngrok-specific optimizations
"""

import sys
import os
import socket

print("=== Starting MatchPulse Ngrok Edition ===")

try:
    # Load environment variables FIRST
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded")

    # Debug environment loading
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///matchpulse_ngrok.db')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ngrok-matchpulse-secret')
    PORT = os.environ.get('PORT', '5000')
    
    print(f"DATABASE_URL: {DATABASE_URL[:50]}...")
    print(f"SECRET_KEY: {'Found' if SECRET_KEY != 'ngrok-matchpulse-secret' else 'Using default'}")
    print(f"PORT: {PORT}")

    # Import Flask components
    from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
    from flask_socketio import SocketIO, emit
    print("✅ Flask imports successful")

    # Import database components (prefer SQLite for ngrok simplicity)
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        POSTGRES_AVAILABLE = True
        print("✅ PostgreSQL driver available")
    except ImportError:
        import sqlite3
        POSTGRES_AVAILABLE = False
        print("❌ PostgreSQL driver not available, using SQLite")

    # Import other components
    import qrcode
    import openpyxl
    from openpyxl import Workbook
    import uuid
    import json
    from datetime import datetime
    from cryptography.fernet import Fernet
    import threading
    import time
    from functools import lru_cache, wraps
    import base64
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    import secrets
    import string
    from flask import session
    print("✅ All imports successful", flush=True)

    # Create Flask app optimized for ngrok
    app = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEY
    
    # Admin email and page-specific passwords
    ADMIN_EMAIL = 'takshgandhi4@gmail.com'
    
    # Google Form Configuration for Feedback
    GOOGLE_FORM_ID = "1FAIpQLSe_YOUR_GOOGLE_FORM_ID_HERE"  # Replace with your actual Google Form ID
    GOOGLE_FORM_TEAM_ID_FIELD = "entry.123456789"  # Replace with actual entry field ID for Team ID
    GOOGLE_FORM_PLAYER1_FIELD = "entry.987654321"  # Replace with actual entry field ID for Player 1
    GOOGLE_FORM_PLAYER2_FIELD = "entry.456789123"  # Replace with actual entry field ID for Player 2
    
    # Password file to store generated passwords
    PASSWORD_FILE = 'page_passwords.json'
    
    def generate_random_password(length=8):
        """Generate a random password with letters and numbers"""
        import string
        import random
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))
    
    def load_or_generate_passwords():
        """Load existing passwords or generate new ones if file doesn't exist"""
        if os.path.exists(PASSWORD_FILE):
            try:
                with open(PASSWORD_FILE, 'r') as f:
                    passwords = json.load(f)
                print("✅ Loaded existing passwords from file", flush=True)
                return passwords, False  # False means passwords weren't newly generated
            except Exception as e:
                print(f"⚠️ Error loading passwords file: {e}", flush=True)
        
        # Generate new passwords
        print("🔄 Generating new random passwords...", flush=True)
        passwords = {
            'Register': generate_random_password(8),
            'Validate': generate_random_password(8), 
            'Monitor': generate_random_password(8),
            'Admin': generate_random_password(8)
        }
        
        # Save passwords to file
        try:
            with open(PASSWORD_FILE, 'w') as f:
                json.dump(passwords, f, indent=2)
            print("✅ Saved new passwords to file", flush=True)
        except Exception as e:
            print(f"❌ Error saving passwords file: {e}", flush=True)
        
        return passwords, True  # True means passwords were newly generated
    
    # Load or generate passwords
    PAGE_PASSWORDS, passwords_newly_generated = load_or_generate_passwords()
    
    # Utility function for mobile number formatting
    def format_mobile_for_display(phone):
        """Format mobile number for display purposes"""
        if not phone:
            return None
        
        # Remove any existing formatting
        digits = ''.join(filter(str.isdigit, phone))
        
        # Format as +91 XXXXX XXXXX for display
        if len(digits) == 10:
            return f"+91 {digits[:5]} {digits[5:]}"
        elif len(digits) == 12 and digits.startswith('91'):
            return f"+91 {digits[2:7]} {digits[7:]}"
        else:
            return phone  # Return as-is if format is unexpected
    
    # Ngrok-specific optimizations
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # No caching for development
    app.config['TEMPLATES_AUTO_RELOAD'] = True  # Auto-reload templates for ngrok
    app.config['JSON_SORT_KEYS'] = False  # Don't sort JSON keys for faster response
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False  # Disable JSON pretty printing
    
    # Email configuration
    app.config['MAIL_SERVER'] = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('SMTP_PORT', 587))
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = os.environ.get('SMTP_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('SMTP_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('SMTP_USERNAME')

    socketio = SocketIO(app, cors_allowed_origins="*")

    # Excel file path and in-memory storage
    EXCEL_FILE = 'teams_backup_ngrok.xlsx'
    teams_data = []
    
    # Simple cache for ngrok (no complex TTL)
    cache = {
        'stats': {'data': None, 'timestamp': 0},
        'teams': {'data': None, 'timestamp': 0},
        'admin_teams': {'data': None, 'timestamp': 0},
    }

    print("✅ Flask app and SocketIO created", flush=True)
    
    # Simple cache helper functions for ngrok
    def get_cached_data(cache_key, max_age=30):
        """Get data from cache if not too old"""
        cache_entry = cache.get(cache_key, {})
        current_time = time.time()
        
        if (cache_entry.get('data') is not None and 
            current_time - cache_entry.get('timestamp', 0) < max_age):
            return cache_entry['data']
        return None
    
    def set_cached_data(cache_key, data):
        """Set data in cache with timestamp"""
        cache[cache_key]['data'] = data
        cache[cache_key]['timestamp'] = time.time()
    
    def invalidate_cache():
        """Clear all cached data when data changes"""
        for key in cache:
            cache[key]['data'] = None
            cache[key]['timestamp'] = 0

    # Authentication functions
    def send_all_passwords_email(newly_generated=False):
        """Send all page passwords in one email at startup"""
        try:
            msg = MIMEMultipart()
            subject_prefix = "🆕 NEW" if newly_generated else "📋 CURRENT"
            msg['Subject'] = f'{subject_prefix} MatchPulse - All Access Passwords'
            msg['From'] = app.config['MAIL_USERNAME']
            msg['To'] = ADMIN_EMAIL
            
            # Create password table HTML
            password_rows = ""
            for page, password in PAGE_PASSWORDS.items():
                password_rows += f"""
                <tr>
                    <td style="padding: 15px; border: 1px solid rgba(0, 102, 255, 0.3); background: rgba(0, 102, 255, 0.1); font-weight: bold; color: #ffffff; font-size: 15px;">{page}</td>
                    <td style="padding: 15px; border: 1px solid rgba(0, 102, 255, 0.3); background: linear-gradient(45deg, #0066ff, #ff0033); color: white; font-family: 'Courier New', monospace; font-size: 16px; font-weight: bold; text-align: center;">{password}</td>
                </tr>
                """
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: 'Arial', sans-serif; line-height: 1.6; color: #333333; background: #f8f9fa; margin: 0; padding: 0; }}
                    .container {{ max-width: 700px; margin: 0 auto; padding: 20px; background: white; }}
                    .header {{ background: linear-gradient(135deg, #1e5aa8 0%, #c41e3a 100%); color: white; padding: 25px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: white; padding: 25px; border-radius: 0 0 10px 10px; border: 1px solid #e0e0e0; }}
                    .password-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0; }}
                    .info {{ background: #f0f4ff; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #1e5aa8; }}
                    .note {{ background: #fff5f5; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #c41e3a; }}
                    .team-title {{ color: #1e5aa8; font-weight: bold; font-size: 24px; margin: 10px 0; }}
                    .highlight-blue {{ color: #1e5aa8; font-weight: bold; }}
                    .highlight-red {{ color: #c41e3a; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="team-title">🔐 <span style="color: #87ceeb;">TEAM RAW</span> - <span style="color: #ffb6c1;">ACCESS PASSWORDS</span></div>
                        {'<div style="background: rgba(196, 30, 58, 0.2); padding: 10px; margin-top: 12px; border-radius: 6px; border: 1px solid #c41e3a;"><strong style="font-size: 14px;">🆕 NEW PASSWORDS GENERATED</strong></div>' if newly_generated else ''}
                    </div>
                    <div class="content">
                        <h2 style="color: #1e5aa8; font-size: 20px; margin-bottom: 15px;">{'🆕 New Passwords' if newly_generated else '📋 Current Passwords'}</h2>
                        <p style="color: #333333; font-size: 14px; line-height: 1.6; margin-bottom: 20px;">
                            {'New random passwords have been generated for your TEAM RAW system:' if newly_generated else 'Here are the current passwords for your TEAM RAW system:'}
                        </p>
                        
                        <table class="password-table">
                            <thead>
                                <tr style="background: linear-gradient(45deg, #0066ff, #ff0033); color: white;">
                                    <th style="padding: 15px; border: none; font-size: 16px; font-weight: bold;">Page</th>
                                    <th style="padding: 15px; border: none; font-size: 16px; font-weight: bold;">Password</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr style="background: rgba(40, 167, 69, 0.2);">
                                    <td style="padding: 15px; border: 1px solid rgba(0, 102, 255, 0.3); background: rgba(40, 167, 69, 0.2); font-weight: bold; color: #ffffff;">Home</td>
                                    <td style="padding: 15px; border: 1px solid rgba(0, 102, 255, 0.3); background: rgba(40, 167, 69, 0.2); color: #28a745; font-weight: bold; font-size: 16px;">No Password Required</td>
                                </tr>
                                {password_rows}
                            </tbody>
                        </table>
                        
                        <div class="info">
                            <h4 style="color: #3399ff; font-size: 18px; margin-bottom: 15px;">📋 System Details:</h4>
                            <p style="color: #ffffff; font-size: 15px; margin: 10px 0;"><strong class="highlight-white">{'Generated' if newly_generated else 'Loaded'}:</strong> <span class="highlight-blue">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span></p>
                            <p style="color: #ffffff; font-size: 15px; margin: 10px 0;"><strong class="highlight-white">Total Protected Pages:</strong> <span class="highlight-red">{len(PAGE_PASSWORDS)}</span></p>
                            <p style="color: #ffffff; font-size: 15px; margin: 10px 0;"><strong class="highlight-white">Public Pages:</strong> <span class="highlight-blue">Home, Queue (no password required)</span></p>
                            {'<p style="color: #ffffff; font-size: 15px; margin: 10px 0;"><strong class="highlight-white">Status:</strong> <span class="highlight-red">🆕 New random passwords generated and saved</span></p>' if newly_generated else '<p style="color: #ffffff; font-size: 15px; margin: 10px 0;"><strong class="highlight-white">Status:</strong> <span class="highlight-blue">📋 Existing passwords loaded from file</span></p>'}
                        </div>
                        
                        <div class="note">
                            <h4 style="color: #ff3366; font-size: 18px; margin-bottom: 15px;">📝 Important Security Notes:</h4>
                            <ul style="color: #ffffff; font-size: 15px; line-height: 1.8;">
                                <li><strong class="highlight-red">{'🆕 These are NEW randomly generated passwords' if newly_generated else '📋 These are your current saved passwords'}</strong></li>
                                <li><strong class="highlight-white">Save this email</strong> for future reference and secure access</li>
                                <li><strong class="highlight-blue">Passwords are case-sensitive</strong> - enter exactly as shown</li>
                                <li><strong class="highlight-white">Each page requires</strong> its specific password for access</li>
                                <li><strong class="highlight-red">Sessions expire</strong> when browser is closed for security</li>
                                <li><strong class="highlight-blue">Home and Queue pages</strong> are accessible without password</li>
                                {'<li><strong class="highlight-white">🔄 Passwords will remain the same</strong> until manually regenerated</li>' if newly_generated else ''}
                            </ul>
                        </div>
                        
                        <div style="text-align: center; margin: 30px 0; padding: 20px; background: rgba(51, 153, 255, 0.15); border-radius: 12px; border: 1px solid rgba(51, 153, 255, 0.3);">
                            <p style="color: #3399ff; font-size: 18px; font-weight: bold; margin: 0;">
                                <span style="color: #ff3366;">TEAM RAW</span> ROBOTICS COMPETITION SYSTEM 🏆
                            </p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
            server.quit()
            
            print(f"✅ All passwords sent to {ADMIN_EMAIL}", flush=True)
            return True
            
        except Exception as e:
            print(f"❌ Failed to send passwords email: {e}", flush=True)
            return False

    def login_required(page_name):
        """Decorator to require login for pages with page-specific passwords"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Check if user is logged in for this page
                if f'logged_in_{page_name}' not in session:
                    # Set the page-specific password
                    page_password = PAGE_PASSWORDS.get(page_name)
                    if page_password:
                        session[f'password_{page_name}'] = page_password
                        
                        # Show login page without sending email (passwords already sent at startup)
                        flash(f'Use the {page_name} page password from your startup email', 'info')
                        return render_template('login.html', page_name=page_name)
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator 
   # Database configuration (prefer SQLite for ngrok)
    USE_POSTGRES = DATABASE_URL.startswith('postgresql://') and POSTGRES_AVAILABLE
    if not USE_POSTGRES:
        DATABASE_URL = 'sqlite:///matchpulse_ngrok.db'
    print(f"✅ Database type: {'PostgreSQL' if USE_POSTGRES else 'SQLite'}", flush=True)

    # Encryption key
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
    if not ENCRYPTION_KEY:
        ENCRYPTION_KEY = Fernet.generate_key()
        print("⚠️ Generated new encryption key for ngrok session")
    else:
        if isinstance(ENCRYPTION_KEY, str):
            ENCRYPTION_KEY = ENCRYPTION_KEY.encode()
    
    cipher_suite = Fernet(ENCRYPTION_KEY)
    print("✅ Encryption configured", flush=True)

    def get_db_connection():
        """Get database connection"""
        try:
            if USE_POSTGRES:
                db_url = DATABASE_URL
                if 'channel_binding=require' in db_url:
                    db_url = db_url.replace('&channel_binding=require', '').replace('?channel_binding=require&', '?').replace('?channel_binding=require', '')
                conn = psycopg2.connect(db_url)
                return conn
            else:
                # Use SQLite for ngrok
                db_path = DATABASE_URL.replace('sqlite:///', '') if DATABASE_URL.startswith('sqlite://') else 'matchpulse_ngrok.db'
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                return conn
        except Exception as e:
            print(f"❌ Database connection error: {e}", flush=True)
            return None

    def get_cursor(conn):
        """Get appropriate cursor for database type"""
        if USE_POSTGRES:
            return conn.cursor(cursor_factory=RealDictCursor)
        else:
            return conn.cursor()

    def execute_query(query, params=None, fetch_one=False, fetch_all=False):
        """Execute database query with proper parameter substitution"""
        conn = get_db_connection()
        if not conn:
            return False
        
        try:
            cur = get_cursor(conn)
            
            # Convert PostgreSQL-style parameters (%s) to SQLite-style (?) if needed
            if not USE_POSTGRES and query.count('%s') > 0:
                query = query.replace('%s', '?')
            
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            
            result = None
            if fetch_one:
                result = cur.fetchone()
                if result and not USE_POSTGRES:
                    result = dict(result)
            elif fetch_all:
                result = cur.fetchall()
                if result and not USE_POSTGRES:
                    result = [dict(row) for row in result]
            else:
                result = True
            
            conn.commit()
            cur.close()
            conn.close()
            return result
        except Exception as e:
            print(f"Database query error: {e}", flush=True)
            if conn:
                conn.close()
            return False

    def init_database():
        """Initialize database tables"""
        print("=== Initializing Database ===", flush=True)
        try:
            conn = get_db_connection()
            if conn:
                cur = conn.cursor()
                if USE_POSTGRES:
                    cur.execute('''
                        CREATE TABLE IF NOT EXISTS teams (
                            team_id VARCHAR(50) PRIMARY KEY,
                            player1_name VARCHAR(100) NOT NULL,
                            player1_pid VARCHAR(20),
                            player1_phone VARCHAR(20),
                            player2_name VARCHAR(100) NOT NULL,
                            player2_pid VARCHAR(20),
                            player2_phone VARCHAR(20),
                            email VARCHAR(255),
                            payment_status VARCHAR(20) DEFAULT 'Pending',
                            payment_amount DECIMAL(10,2),
                            payment_method VARCHAR(50),
                            qr_code_path VARCHAR(200),
                            validation_status VARCHAR(20) DEFAULT 'Not Validated',
                            match_status VARCHAR(20) DEFAULT 'Waiting',
                            queue_number INTEGER,
                            group_id INTEGER DEFAULT 1,
                            sequence_order INTEGER,
                            goal_time DECIMAL(8,3),
                            goal_recorded_at TIMESTAMP,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            validated_at TIMESTAMP
                        )
                    ''')
                else:
                    cur.execute('''
                        CREATE TABLE IF NOT EXISTS teams (
                            team_id TEXT PRIMARY KEY,
                            player1_name TEXT NOT NULL,
                            player1_pid TEXT,
                            player1_phone TEXT,
                            player2_name TEXT NOT NULL,
                            player2_pid TEXT,
                            player2_phone TEXT,
                            email TEXT,
                            payment_status TEXT DEFAULT 'Pending',
                            payment_amount REAL,
                            payment_method TEXT,
                            qr_code_path TEXT,
                            validation_status TEXT DEFAULT 'Not Validated',
                            match_status TEXT DEFAULT 'Waiting',
                            queue_number INTEGER,
                            group_id INTEGER DEFAULT 1,
                            sequence_order INTEGER,
                            goal_time REAL,
                            goal_recorded_at DATETIME,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            validated_at DATETIME
                        )
                    ''')
                conn.commit()
                cur.close()
                conn.close()
                print(f"✅ Database initialized successfully ({'PostgreSQL' if USE_POSTGRES else 'SQLite'})", flush=True)
                
                # Run database migrations
                migrate_database()
                
            else:
                print("❌ Could not connect to database", flush=True)
        except Exception as e:
            print(f"❌ Database initialization error: {e}", flush=True)

    def migrate_database():
        """Add missing columns to existing database"""
        try:
            conn = get_db_connection()
            if conn:
                cur = conn.cursor()
                
                # Check if columns exist and add them if they don't
                if USE_POSTGRES:
                    # Check if columns exist in PostgreSQL
                    cur.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name = 'teams' AND column_name IN ('player1_pid', 'player2_pid', 'player1_phone', 'player2_phone', 'queue_number', 'group_id', 'sequence_order', 'goal_time', 'goal_recorded_at')
                    """)
                    existing_columns = [row[0] for row in cur.fetchall()]
                    
                    if 'player1_pid' not in existing_columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN player1_pid VARCHAR(20)')
                        print("✅ Added player1_pid column to PostgreSQL", flush=True)
                    
                    if 'player2_pid' not in existing_columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN player2_pid VARCHAR(20)')
                        print("✅ Added player2_pid column to PostgreSQL", flush=True)
                    
                    if 'player1_phone' not in existing_columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN player1_phone VARCHAR(20)')
                        print("✅ Added player1_phone column to PostgreSQL", flush=True)
                    
                    if 'player2_phone' not in existing_columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN player2_phone VARCHAR(20)')
                        print("✅ Added player2_phone column to PostgreSQL", flush=True)
                    
                    if 'goal_time' not in existing_columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN goal_time DECIMAL(8,3)')
                        print("✅ Added goal_time column to PostgreSQL", flush=True)
                    
                    if 'queue_number' not in existing_columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN queue_number INTEGER')
                        print("✅ Added queue_number column to PostgreSQL", flush=True)
                    
                    if 'group_id' not in existing_columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN group_id INTEGER DEFAULT 1')
                        print("✅ Added group_id column to PostgreSQL", flush=True)
                    
                    if 'sequence_order' not in existing_columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN sequence_order INTEGER')
                        print("✅ Added sequence_order column to PostgreSQL", flush=True)
                    
                    if 'goal_recorded_at' not in existing_columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN goal_recorded_at TIMESTAMP')
                        print("✅ Added goal_recorded_at column to PostgreSQL", flush=True)
                        
                else:
                    # Check if columns exist in SQLite
                    cur.execute("PRAGMA table_info(teams)")
                    columns = [row[1] for row in cur.fetchall()]
                    
                    if 'player1_pid' not in columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN player1_pid TEXT')
                        print("✅ Added player1_pid column to SQLite", flush=True)
                    
                    if 'player2_pid' not in columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN player2_pid TEXT')
                        print("✅ Added player2_pid column to SQLite", flush=True)
                    
                    if 'player1_phone' not in columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN player1_phone TEXT')
                        print("✅ Added player1_phone column to SQLite", flush=True)
                    
                    if 'player2_phone' not in columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN player2_phone TEXT')
                        print("✅ Added player2_phone column to SQLite", flush=True)
                    
                    if 'goal_time' not in columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN goal_time REAL')
                        print("✅ Added goal_time column to SQLite", flush=True)
                    
                    if 'queue_number' not in columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN queue_number INTEGER')
                        print("✅ Added queue_number column to SQLite", flush=True)
                    
                    if 'group_id' not in columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN group_id INTEGER DEFAULT 1')
                        print("✅ Added group_id column to SQLite", flush=True)
                    
                    if 'sequence_order' not in columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN sequence_order INTEGER')
                        print("✅ Added sequence_order column to SQLite", flush=True)
                    
                    if 'goal_recorded_at' not in columns:
                        cur.execute('ALTER TABLE teams ADD COLUMN goal_recorded_at DATETIME')
                        print("✅ Added goal_recorded_at column to SQLite", flush=True)
                
                conn.commit()
                cur.close()
                conn.close()
                print("✅ Database migration completed", flush=True)
                
        except Exception as e:
            print(f"⚠️ Database migration error: {e}", flush=True)

    def assign_queue_number(group_id=1):
        """Assign the next queue number for a group"""
        try:
            # Get the highest queue number for the group
            result = execute_query('''
                SELECT MAX(queue_number) as max_queue 
                FROM teams 
                WHERE group_id = %s
            ''', (group_id,), fetch_one=True)
            
            max_queue = result['max_queue'] if result and result['max_queue'] else 0
            return max_queue + 1
            
        except Exception as e:
            print(f"Error assigning queue number: {e}")
            return 1

    def assign_sequence_order():
        """Assign sequence order based on validation time"""
        try:
            # Get all validated teams without sequence order
            teams = execute_query('''
                SELECT team_id FROM teams 
                WHERE validation_status = 'Validated' 
                AND sequence_order IS NULL 
                ORDER BY validated_at ASC
            ''', fetch_all=True)
            
            if teams:
                for i, team in enumerate(teams):
                    execute_query('''
                        UPDATE teams 
                        SET sequence_order = %s 
                        WHERE team_id = %s
                    ''', (i + 1, team['team_id']))
                
                print(f"✅ Assigned sequence order to {len(teams)} teams")
                
        except Exception as e:
            print(f"Error assigning sequence order: {e}")

    def init_excel():
        """Initialize Excel backup file"""
        try:
            if not os.path.exists(EXCEL_FILE):
                wb = Workbook()
                ws = wb.active
                ws.title = "Teams"
                headers = ['Team ID', 'Player 1 Name', 'Player 2 Name', 'Email', 'Payment Status', 
                          'Payment Amount', 'Payment Method', 'QR Code Path', 'Validation Status', 
                          'Match Status', 'Created At', 'Validated At']
                ws.append(headers)
                wb.save(EXCEL_FILE)
                print("✅ Excel backup file initialized", flush=True)
            else:
                print("✅ Excel backup file already exists", flush=True)
        except Exception as e:
            print(f"❌ Excel initialization error: {e}", flush=True)

    def generate_qr_data(team_id):
        """Generate encrypted QR code data"""
        data = {
            'team_id': team_id,
            'timestamp': datetime.now().isoformat(),
            'app': 'MatchPulse-Ngrok'
        }
        encrypted_data = cipher_suite.encrypt(json.dumps(data).encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()

    def generate_qr_code(team_id, qr_data):
        """Generate QR code image"""
        if not os.path.exists('static/qr_codes'):
            os.makedirs('static/qr_codes')
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        qr_path = f'static/qr_codes/{team_id}.png'
        img.save(qr_path)
        return qr_path

    def send_qr_email(email, team_id, player1_name, player2_name, qr_path, queue_number=None, group_id=None):
        """Send QR code via email using SMTP directly"""
        try:
            print(f"Sending QR code email to {email}...", flush=True)
            
            msg = MIMEMultipart('related')
            msg['Subject'] = f'TEAM RAW - Team {team_id} Mission QR Code & Details'
            msg['From'] = app.config['MAIL_USERNAME']
            msg['To'] = email
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: 'Arial', sans-serif; line-height: 1.6; color: #333333; background: #f8f9fa; margin: 0; padding: 0; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background: white; }}
                    .header {{ background: linear-gradient(135deg, #1e5aa8 0%, #c41e3a 100%); color: white; padding: 25px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .logo {{ width: 70px; height: 70px; border-radius: 10px; margin-bottom: 10px; border: 2px solid white; }}
                    .content {{ background: white; padding: 25px; border-radius: 0 0 10px 10px; border: 1px solid #e0e0e0; }}
                    .qr-container {{ text-align: center; margin: 20px 0; padding: 20px; background: #f8f9ff; border-radius: 10px; border: 2px solid #1e5aa8; }}
                    .qr-code {{ max-width: 180px; border: 3px solid #1e5aa8; border-radius: 10px; padding: 10px; background: white; }}
                    .team-info {{ background: #f0f4ff; padding: 20px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #1e5aa8; }}
                    .instructions {{ background: #fff5f5; padding: 20px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #c41e3a; }}
                    .social-links {{ text-align: center; margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 10px; }}
                    .social-btn {{ display: inline-block; margin: 0 8px; padding: 10px 20px; background: linear-gradient(45deg, #1e5aa8, #c41e3a); color: white; text-decoration: none; border-radius: 20px; font-weight: bold; font-size: 13px; }}
                    .footer {{ text-align: center; margin-top: 20px; color: #666666; font-size: 12px; }}
                    .team-title {{ color: #1e5aa8; font-weight: bold; font-size: 24px; margin: 10px 0; }}
                    .mission-badge {{ background: linear-gradient(45deg, #1e5aa8, #c41e3a); color: white; padding: 8px 16px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
                    .highlight-blue {{ color: #1e5aa8; font-weight: bold; }}
                    .highlight-red {{ color: #c41e3a; font-weight: bold; }}
                    .highlight-dark {{ color: #333333; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="cid:team_logo" alt="TEAM RAW Logo" class="logo">
                        <div class="team-title"><span style="color: #87ceeb;">TEAM</span> <span style="color: #ffb6c1;">RAW</span></div>
                        <div style="font-size: 16px; margin: 8px 0;">Robotics Competition</div>
                        <span class="mission-badge">TEAM REGISTRATION</span>
                    </div>
                    <div class="content">
                        <div class="team-info">
                            <h3 style="color: #1e5aa8; font-size: 18px; margin-bottom: 15px;">Team Details</h3>
                            <p style="font-size: 14px; margin: 8px 0;"><strong class="highlight-dark">Team ID:</strong> <span class="highlight-blue">{team_id}</span></p>
                            <p style="font-size: 14px; margin: 8px 0;"><strong class="highlight-dark">Player 1:</strong> <span class="highlight-blue">{player1_name}</span></p>
                            <p style="font-size: 14px; margin: 8px 0;"><strong class="highlight-dark">Player 2:</strong> <span class="highlight-red">{player2_name}</span></p>
                            {f'<p style="font-size: 14px; margin: 8px 0;"><strong class="highlight-dark">🎯 Queue Position:</strong> <span style="background: linear-gradient(45deg, #1e5aa8, #c41e3a); padding: 4px 12px; border-radius: 8px; font-weight: bold; color: white; font-size: 14px;">#{queue_number}</span></p>' if queue_number else ''}
                            {f'<p style="font-size: 14px; margin: 8px 0;"><strong class="highlight-dark">Group:</strong> <span class="highlight-blue">{group_id}</span></p>' if group_id else ''}
                        </div>
                        
                        <div class="qr-container">
                            <h3 style="color: #1e5aa8; font-size: 16px; margin-bottom: 15px;">🔐 Your QR Code</h3>
                            <img src="cid:qr_code" alt="Team QR Code" class="qr-code">
                            <p style="margin-top: 10px; color: #c41e3a; font-size: 14px;"><strong>Present this at the competition</strong></p>
                        </div>
                        
                        <div class="instructions">
                            <h3 style="color: #c41e3a; font-size: 16px; margin-bottom: 12px;">� InstIructions:</h3>
                            <ul style="color: #333333; font-size: 14px; line-height: 1.6; margin: 0; padding-left: 20px;">
                                <li><strong>Save this QR code</strong> to your device</li>
                                <li><strong>Present at competition</strong> for team validation</li>
                                <li><strong>Remember your Team ID:</strong> <span class="highlight-blue">{team_id}</span></li>
                                {f'<li><strong class="highlight-red">Queue Position: #{queue_number}</strong> - Your turn order</li>' if queue_number else ''}
                                {f'<li><strong>Group Assignment:</strong> <span class="highlight-blue">{group_id}</span></li>' if group_id else ''}
                            </ul>
                            {f'<div style="background: #e8f2ff; padding: 15px; border-radius: 8px; margin-top: 15px; border-left: 4px solid #1e5aa8;"><strong style="color: #1e5aa8; font-size: 14px;">Competition Order:</strong><br><span style="color: #333333; font-size: 13px;">Your team is position <strong class="highlight-red">#{queue_number}</strong> in the queue. Please be ready when called!</span></div>' if queue_number else ''}
                        </div>
                        
                        <div class="social-links">
                            <h3 style="color: #c41e3a; margin-bottom: 12px; font-size: 16px;">🌐 Follow TEAM RAW</h3>
                            <a href="https://www.instagram.com/teamraw_robotics" class="social-btn">
                                📸 Instagram
                            </a>
                            <a href="https://www.linkedin.com/company/team-raw-robotics" class="social-btn">
                                💼 LinkedIn
                            </a>
                            <p style="margin-top: 12px; color: #666666; font-size: 12px;">
                                Follow us for updates and robotics content!
                            </p>
                        </div>
                        
                        <div style="text-align: center; margin: 20px 0; padding: 15px; background: #f0f4ff; border-radius: 8px;">
                            <p style="color: #1e5aa8; font-size: 16px; font-weight: bold; margin: 0;">
                                🚀 Good Luck in the Competition! 🏆
                            </p>
                        </div>
                    </div>
                    <div class="footer">
                        <p style="color: #666666; font-size: 12px;">TEAM RAW Robotics Competition</p>
                        <p style="color: #1e5aa8; font-size: 11px;">Powered by Innovation</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create alternative container
            msg_alternative = MIMEMultipart('alternative')
            msg.attach(msg_alternative)
            
            # Add HTML part
            html_part = MIMEText(html_body, 'html')
            msg_alternative.attach(html_part)
            
            # Attach QR code image
            with open(qr_path, 'rb') as f:
                qr_image_data = f.read()
                qr_image = MIMEImage(qr_image_data)
                qr_image.add_header('Content-ID', '<qr_code>')
                qr_image.add_header('Content-Disposition', 'inline', filename=f'team_{team_id}_qr.png')
                msg.attach(qr_image)
            
            # Attach TEAM RAW logo
            logo_path = 'static/images/RawLogo.jpeg'
            if os.path.exists(logo_path):
                with open(logo_path, 'rb') as f:
                    logo_image_data = f.read()
                    logo_image = MIMEImage(logo_image_data)
                    logo_image.add_header('Content-ID', '<team_logo>')
                    logo_image.add_header('Content-Disposition', 'inline', filename='team_raw_logo.jpeg')
                    msg.attach(logo_image)
            
            # Send email using SMTP
            server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Email sent successfully to {email}", flush=True)
            
        except Exception as e:
            print(f"❌ Email sending failed: {e}", flush=True)
            raise e

    # Login route
    @app.route('/login/<page_name>', methods=['POST'])
    def login(page_name):
        """Handle login for specific pages"""
        entered_password = request.form.get('password')
        correct_password = session.get(f'password_{page_name}')
        
        if entered_password == correct_password:
            session[f'logged_in_{page_name}'] = True
            flash('Access granted!', 'success')
            
            # Redirect to the appropriate page
            if page_name == 'Home':
                return redirect(url_for('index'))
            elif page_name == 'Register':
                return redirect(url_for('register_page'))
            elif page_name == 'Validate':
                return redirect(url_for('validate_page'))
            elif page_name == 'Monitor':
                return redirect(url_for('monitor_dashboard'))
            elif page_name == 'Admin':
                return redirect(url_for('admin_panel'))
        else:
            flash('Invalid password!', 'error')
            return render_template('login.html', page_name=page_name)

    # Routes - All from original app_minimal_working.py with authentication
    @app.route('/')
    def index():
        """Home page with navigation - No password required"""
        return render_template('index.html')

    @app.route('/register')
    @login_required('Register')
    def register_page():
        """Team registration page"""
        return render_template('register.html')

    @app.route('/register', methods=['POST'])
    def register_team():
        """Handle team registration"""
        try:
            print("🔄 Processing team registration...", flush=True)
            player1_name = request.form.get('player1_name')
            player1_pid = request.form.get('player1_pid', '').strip()
            player1_phone_raw = request.form.get('player1_phone', '').strip()
            player2_name = request.form.get('player2_name')
            player2_pid = request.form.get('player2_pid', '').strip()
            player2_phone_raw = request.form.get('player2_phone', '').strip()
            email = request.form.get('email', '').strip()
            
            # Validate and format mobile numbers
            def validate_and_format_mobile(phone_raw):
                if not phone_raw:
                    return None
                
                # Remove all non-digits
                phone_digits = ''.join(filter(str.isdigit, phone_raw))
                
                # Check if it's a valid Indian mobile number
                if len(phone_digits) == 10 and phone_digits[0] in '6789':
                    return f"+91{phone_digits}"
                elif len(phone_digits) == 12 and phone_digits.startswith('91') and phone_digits[2] in '6789':
                    return f"+{phone_digits}"
                elif len(phone_digits) == 13 and phone_digits.startswith('91') and phone_digits[2] in '6789':
                    return f"+{phone_digits}"
                else:
                    raise ValueError(f"Invalid mobile number format: {phone_raw}")
            
            try:
                player1_phone = validate_and_format_mobile(player1_phone_raw)
                player2_phone = validate_and_format_mobile(player2_phone_raw)
            except ValueError as e:
                flash(f'Mobile number error: {str(e)}', 'error')
                return render_template('register.html')
            payment_status = request.form.get('payment_status', 'Pending')
            payment_amount = request.form.get('payment_amount')
            payment_method = request.form.get('payment_method', '').strip()
            
            if not player1_name or not player2_name:
                flash('Both player names are required', 'error')
                return redirect(url_for('register_page'))
            
            # Convert payment amount to float if provided
            payment_amount_float = None
            if payment_amount:
                try:
                    payment_amount_float = float(payment_amount)
                except ValueError:
                    flash('Invalid payment amount', 'error')
                    return redirect(url_for('register_page'))
            
            # Generate unique team ID
            team_id = str(uuid.uuid4())[:8].upper()
            print(f"🔄 Generated team ID: {team_id}", flush=True)
            
            # Assign queue number and group
            group_id = 1  # Default group, can be modified later
            queue_number = assign_queue_number(group_id)
            print(f"🔄 Assigned queue number: {queue_number} for group {group_id}", flush=True)
            
            # Generate QR code
            print(f"🔄 Generating QR code for team {team_id}...", flush=True)
            qr_data = generate_qr_data(team_id)
            qr_path = generate_qr_code(team_id, qr_data)
            print(f"✅ QR code generated: {qr_path}", flush=True)
            
            # Store in database (with fallback for databases without new columns)
            try:
                execute_query('''
                    INSERT INTO teams (team_id, player1_name, player1_pid, player1_phone, player2_name, player2_pid, player2_phone,
                                     email, payment_status, payment_amount, payment_method, qr_code_path, queue_number, group_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (team_id, player1_name, player1_pid or None, player1_phone or None, player2_name, player2_pid or None, player2_phone or None,
                      email or None, payment_status, payment_amount_float, payment_method or None, qr_path, queue_number, group_id))
            except Exception as db_error:
                if 'player1_pid' in str(db_error) or 'player2_pid' in str(db_error) or 'player1_phone' in str(db_error) or 'player2_phone' in str(db_error):
                    # Fallback: Insert without new columns for older database schema
                    print("⚠️ New columns not found, inserting with basic fields", flush=True)
                    execute_query('''
                        INSERT INTO teams (team_id, player1_name, player2_name, email, payment_status, 
                                         payment_amount, payment_method, qr_code_path)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''', (team_id, player1_name, player2_name, email or None, payment_status, 
                          payment_amount_float, payment_method or None, qr_path))
                    flash('Team registered successfully! (New fields not available - please run database migration)', 'warning')
                else:
                    raise db_error
            
            # Invalidate cache after data change
            invalidate_cache()
            
            # Send email with QR code if email provided
            email_sent = False
            if email and app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
                try:
                    send_qr_email(email, team_id, player1_name, player2_name, qr_path, queue_number, group_id)
                    email_sent = True
                    flash(f'QR code sent to your email! Your queue number is {queue_number}.', 'success')
                except Exception as e:
                    print(f"Email sending failed: {e}", flush=True)
                    flash('Registration successful, but email sending failed. Please download the QR code.', 'warning')
            
            # Emit real-time update
            socketio.emit('team_registered', {
                'team_id': team_id,
                'player1_name': player1_name,
                'player2_name': player2_name,
                'status': 'Registered',
                'email_sent': email_sent
            })
            
            return render_template('registration_success.html', 
                                 team_id=team_id, 
                                 qr_path=qr_path,
                                 player1_name=player1_name,
                                 player1_pid=player1_pid,
                                 player1_phone=player1_phone,
                                 player2_name=player2_name,
                                 player2_pid=player2_pid,
                                 player2_phone=player2_phone,
                                 email=email,
                                 email_sent=email_sent,
                                 payment_amount=payment_amount_float,
                                 payment_method=payment_method,
                                 payment_status=payment_status,
                                 queue_number=queue_number,
                                 group_id=group_id)
            
        except Exception as e:
            print(f"❌ Registration error: {str(e)}", flush=True)
            import traceback
            traceback.print_exc()
            flash(f'Registration failed: {str(e)}', 'error')
            return redirect(url_for('register_page'))

    @app.route('/queue')
    def queue_page():
        """Public queue page to view all teams and their positions"""
        return render_template('queue.html')

    @app.route('/validate')
    @login_required('Validate')
    def validate_page():
        """QR code validation page"""
        return render_template('validate.html')

    @app.route('/validate', methods=['POST'])
    def validate_qr():
        """Handle QR code validation and team ID validation"""
        try:
            # Get data from request
            qr_data = request.json.get('qr_data')
            team_id = request.json.get('team_id')
            
            # Determine team ID from either QR data or direct input
            if team_id:
                team_id = team_id.upper().strip()
            elif qr_data:
                try:
                    # Try encrypted QR data first
                    encrypted_data = base64.urlsafe_b64decode(qr_data.encode())
                    decrypted_data = cipher_suite.decrypt(encrypted_data)
                    data = json.loads(decrypted_data.decode())
                    team_id = data.get('team_id')
                except:
                    # Try simple format like "TEAM:ABC12345"
                    if 'TEAM:' in qr_data:
                        team_id = qr_data.split('TEAM:')[1].strip()
                    else:
                        team_id = qr_data.strip().upper()
            else:
                return jsonify({'success': False, 'message': 'No team ID or QR data provided'})
            
            if not team_id:
                return jsonify({'success': False, 'message': 'Invalid team ID'})
            
            # Check if team exists and validate
            team = execute_query('SELECT * FROM teams WHERE team_id = %s', (team_id,), fetch_one=True)
            
            if not team:
                return jsonify({'success': False, 'message': f'Team {team_id} not found'})
            
            if team['validation_status'] == 'Validated':
                return jsonify({'success': False, 'message': 'Team already validated'})
            
            # Get next sequence order for validated teams
            sequence_result = execute_query('''
                SELECT MAX(sequence_order) as max_sequence 
                FROM teams 
                WHERE validation_status = 'Validated'
            ''', fetch_one=True)
            
            next_sequence = (sequence_result['max_sequence'] or 0) + 1
            
            # Update validation status and set to Playing with sequence order
            execute_query('''
                UPDATE teams 
                SET validation_status = 'Validated', 
                    validated_at = CURRENT_TIMESTAMP,
                    match_status = 'Playing',
                    sequence_order = %s
                WHERE team_id = %s
            ''', (next_sequence, team_id))
            
            # Invalidate cache after data change
            invalidate_cache()
            
            # Emit real-time update
            socketio.emit('team_validated', {
                'team_id': team_id,
                'player1_name': team['player1_name'],
                'player2_name': team['player2_name'],
                'status': 'Playing Now'
            })
            
            return jsonify({
                'success': True, 
                'message': 'Team validated and set to Playing status!',
                'team': {
                    'team_id': team_id,
                    'player1_name': team['player1_name'],
                    'player2_name': team['player2_name'],
                    'status': 'Playing'
                }
            })
            
        except Exception as e:
            return jsonify({'success': False, 'message': f'Validation failed: {str(e)}'})

    @app.route('/monitor')
    @login_required('Monitor')
    def monitor_dashboard():
        """Live monitor dashboard"""
        return render_template('monitor.html')

    @app.route('/monitor/complete_team', methods=['POST'])
    def complete_team_from_monitor():
        """Mark team as completed from monitor dashboard"""
        try:
            team_id = request.json.get('team_id')
            
            if not team_id:
                return jsonify({'success': False, 'message': 'Team ID is required'})
            
            # Get team details first
            team = execute_query('SELECT * FROM teams WHERE team_id = %s', (team_id,), fetch_one=True)
            
            if not team:
                return jsonify({'success': False, 'message': 'Team not found'})
            
            if team['match_status'] != 'Playing':
                return jsonify({'success': False, 'message': f'Team is not currently playing'})
            
            # Update team status to Completed
            result = execute_query('UPDATE teams SET match_status = %s WHERE team_id = %s', 
                                  ('Completed', team_id))
            
            if result:
                # Invalidate cache
                invalidate_cache()
                
                # Send feedback request email
                feedback_sent = False
                if team.get('email') and app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
                    try:
                        send_feedback_request_email(
                            team['email'], 
                            team_id, 
                            team['player1_name'], 
                            team['player2_name']
                        )
                        print(f"✅ Feedback request email sent to {team['email']} for team {team_id}", flush=True)
                        feedback_sent = True
                        
                        # Send admin notification
                        socketio.emit('admin_notification', {
                            'type': 'feedback_sent',
                            'priority': 'normal',
                            'title': '📧 Feedback Email Sent',
                            'message': f"Feedback request sent to {team['email']} for Team {team_id} (Completed without goal time)",
                            'timestamp': datetime.now().isoformat(),
                            'team_id': team_id
                        })
                        
                    except Exception as e:
                        print(f"❌ Failed to send feedback request email: {e}", flush=True)
                        
                        # Send admin notification for email failure
                        socketio.emit('admin_notification', {
                            'type': 'email_failed',
                            'priority': 'high',
                            'title': 'Email Send Failed',
                            'message': f"Failed to send feedback email to Team {team_id}: {str(e)}",
                            'timestamp': datetime.now().isoformat(),
                            'team_id': team_id
                        })
                
                # Emit real-time update
                socketio.emit('team_completed', {
                    'team_id': team_id,
                    'player1_name': team['player1_name'],
                    'player2_name': team['player2_name'],
                    'status': 'Completed'
                })
                
                # Prepare success message based on email status
                if feedback_sent:
                    message = f'Team marked as completed successfully! 📧 Feedback request sent to {team["email"]}.'
                elif team.get('email'):
                    message = f'Team marked as completed successfully! ⚠️ Email sending failed - check admin notifications.'
                else:
                    message = f'Team marked as completed successfully! ℹ️ No email address on file for feedback request.'
                
                return jsonify({
                    'success': True, 
                    'message': message,
                    'feedback_sent': feedback_sent
                })
            
            return jsonify({'success': False, 'message': 'Database update failed'})
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/monitor/record_goal_time', methods=['POST'])
    def record_goal_time():
        """Record goal time for a team"""
        try:
            team_id = request.json.get('team_id')
            goal_time = request.json.get('goal_time')
            
            if not team_id or not goal_time:
                return jsonify({'success': False, 'message': 'Team ID and goal time are required'})
            
            # Validate goal time format (should be in seconds with decimals)
            try:
                goal_time_float = float(goal_time)
                if goal_time_float <= 0:
                    return jsonify({'success': False, 'message': 'Goal time must be positive'})
            except ValueError:
                return jsonify({'success': False, 'message': 'Invalid goal time format'})
            
            # Get team details first
            team = execute_query('SELECT * FROM teams WHERE team_id = %s', (team_id,), fetch_one=True)
            
            if not team:
                return jsonify({'success': False, 'message': 'Team not found'})
            
            # Update team with goal time and mark as completed
            result = execute_query('''
                UPDATE teams 
                SET goal_time = %s, goal_recorded_at = CURRENT_TIMESTAMP, match_status = 'Completed'
                WHERE team_id = %s
            ''', (goal_time_float, team_id))
            
            if result:
                # Invalidate cache
                invalidate_cache()
                
                # Send feedback request email when goal time is recorded
                feedback_sent = False
                if team.get('email') and app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
                    try:
                        send_feedback_request_email(
                            team['email'], 
                            team_id, 
                            team['player1_name'], 
                            team['player2_name']
                        )
                        print(f"✅ Feedback request email sent to {team['email']} for team {team_id} (Goal time: {goal_time_float}s)", flush=True)
                        feedback_sent = True
                        
                        # Send admin notification
                        socketio.emit('admin_notification', {
                            'type': 'feedback_sent',
                            'priority': 'normal',
                            'title': '📧 Feedback Email Sent',
                            'message': f"Feedback request sent to {team['email']} for Team {team_id} (Goal: {goal_time_float}s)",
                            'timestamp': datetime.now().isoformat(),
                            'team_id': team_id,
                            'goal_time': goal_time_float
                        })
                        
                    except Exception as e:
                        print(f"❌ Failed to send feedback request email: {e}", flush=True)
                        
                        # Send admin notification for email failure
                        socketio.emit('admin_notification', {
                            'type': 'email_failed',
                            'priority': 'high',
                            'title': 'Email Send Failed',
                            'message': f"Failed to send feedback email to Team {team_id}: {str(e)}",
                            'timestamp': datetime.now().isoformat(),
                            'team_id': team_id
                        })
                
                # Emit real-time update
                socketio.emit('goal_time_recorded', {
                    'team_id': team_id,
                    'player1_name': team['player1_name'],
                    'player2_name': team['player2_name'],
                    'goal_time': goal_time_float,
                    'status': 'Completed'
                })
                
                # Also emit team completion event for consistency
                socketio.emit('team_completed', {
                    'team_id': team_id,
                    'player1_name': team['player1_name'],
                    'player2_name': team['player2_name'],
                    'goal_time': goal_time_float,
                    'status': 'Completed'
                })
                
                # Prepare success message based on email status
                if feedback_sent:
                    message = f'Goal time {goal_time_float}s recorded successfully! 📧 Feedback request sent to {team["email"]}.'
                elif team.get('email'):
                    message = f'Goal time {goal_time_float}s recorded successfully! ⚠️ Email sending failed - check admin notifications.'
                else:
                    message = f'Goal time {goal_time_float}s recorded successfully! ℹ️ No email address on file for feedback request.'
                
                return jsonify({
                    'success': True, 
                    'message': message,
                    'goal_time': goal_time_float,
                    'feedback_sent': feedback_sent
                })
            
            return jsonify({'success': False, 'message': 'Database update failed'})
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/api/queue')
    def get_queue():
        """Get teams in queue order"""
        try:
            teams = execute_query('''
                SELECT team_id, player1_name, player2_name, queue_number, group_id, 
                       sequence_order, validation_status, match_status, validated_at
                FROM teams 
                ORDER BY group_id ASC, queue_number ASC
            ''', fetch_all=True) or []
            
            # Organize by groups
            groups = {}
            for team in teams:
                group_id = team.get('group_id', 1)
                if group_id not in groups:
                    groups[group_id] = {
                        'group_id': group_id,
                        'teams': []
                    }
                
                groups[group_id]['teams'].append({
                    'team_id': team['team_id'],
                    'team_name': f"{team['player1_name']} & {team['player2_name']}",
                    'player1_name': team['player1_name'],
                    'player2_name': team['player2_name'],
                    'queue_number': team.get('queue_number'),
                    'sequence_order': team.get('sequence_order'),
                    'validation_status': team['validation_status'],
                    'status': team['match_status'].lower() if team['match_status'] else 'waiting',
                    'match_status': team['match_status'],
                    'validated_at': team.get('validated_at')
                })
            
            return jsonify(list(groups.values()))
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/api/playing_queue')
    def get_playing_queue():
        """Get teams in playing sequence order"""
        try:
            teams = execute_query('''
                SELECT team_id, player1_name, player2_name, player1_phone, player2_phone,
                       sequence_order, match_status, validated_at, goal_time
                FROM teams 
                WHERE validation_status = 'Validated'
                ORDER BY sequence_order ASC
            ''', fetch_all=True) or []
            
            playing_queue = []
            for team in teams:
                playing_queue.append({
                    'team_id': team['team_id'],
                    'team_name': f"{team['player1_name']} & {team['player2_name']}",
                    'player1_phone': team.get('player1_phone'),
                    'player2_phone': team.get('player2_phone'),
                    'sequence_order': team.get('sequence_order'),
                    'match_status': team['match_status'],
                    'validated_at': team.get('validated_at'),
                    'goal_time': team.get('goal_time'),
                    'is_current': team['match_status'] == 'Playing',
                    'is_next': False  # Will be set by frontend
                })
            
            # Mark next team
            current_playing = next((i for i, t in enumerate(playing_queue) if t['is_current']), None)
            if current_playing is not None and current_playing + 1 < len(playing_queue):
                playing_queue[current_playing + 1]['is_next'] = True
            elif current_playing is None and playing_queue:
                # No one playing, first waiting team is next
                next_team = next((t for t in playing_queue if t['match_status'] == 'Waiting'), None)
                if next_team:
                    next_team['is_next'] = True
            
            return jsonify(playing_queue)
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/admin/update_queue', methods=['POST'])
    def update_queue_order():
        """Update team queue order"""
        try:
            team_id = request.json.get('team_id')
            new_queue_number = request.json.get('queue_number')
            group_id = request.json.get('group_id', 1)
            
            if not team_id or new_queue_number is None:
                return jsonify({'success': False, 'message': 'Team ID and queue number required'})
            
            # Update queue number
            execute_query('''
                UPDATE teams 
                SET queue_number = %s, group_id = %s 
                WHERE team_id = %s
            ''', (new_queue_number, group_id, team_id))
            
            # Invalidate cache
            invalidate_cache()
            
            return jsonify({'success': True, 'message': 'Queue order updated'})
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/api/leaderboard')
    def get_leaderboard():
        """Get teams sorted by goal time (shortest first)"""
        try:
            teams = execute_query('''
                SELECT team_id, player1_name, player1_phone, player2_name, player2_phone, goal_time, goal_recorded_at, match_status
                FROM teams 
                WHERE goal_time IS NOT NULL 
                ORDER BY goal_time ASC
            ''', fetch_all=True) or []
            
            # Format the data
            leaderboard = []
            for i, team in enumerate(teams):
                player1_display = team['player1_name']
                if team.get('player1_phone'):
                    player1_display += f" ({team['player1_phone']})"
                
                player2_display = team['player2_name']
                if team.get('player2_phone'):
                    player2_display += f" ({team['player2_phone']})"
                
                leaderboard.append({
                    'rank': i + 1,
                    'team_id': team['team_id'],
                    'team_name': f"{player1_display} & {player2_display}",
                    'player1_name': team['player1_name'],
                    'player1_phone': team.get('player1_phone', ''),
                    'player2_name': team['player2_name'],
                    'player2_phone': team.get('player2_phone', ''),
                    'goal_time': float(team['goal_time']),
                    'goal_time_formatted': f"{team['goal_time']:.3f}s",
                    'goal_recorded_at': team['goal_recorded_at'],
                    'match_status': team['match_status']
                })
            
            return jsonify(leaderboard)
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/admin')
    @login_required('Admin')
    def admin_panel():
        """Admin panel with payment calculations"""
        teams = execute_query('SELECT * FROM teams ORDER BY created_at DESC LIMIT 50', fetch_all=True) or []
        
        # Calculate payment statistics
        cash_teams = [t for t in teams if t.get('payment_method') == 'Cash']
        upi_teams = [t for t in teams if t.get('payment_method') == 'UPI']
        cash_revenue = sum([float(t.get('payment_amount', 0) or 0) for t in cash_teams])
        upi_revenue = sum([float(t.get('payment_amount', 0) or 0) for t in upi_teams])
        total_revenue = sum([float(t.get('payment_amount', 0) or 0) for t in teams])
        
        payment_stats = {
            'cash_count': len(cash_teams),
            'upi_count': len(upi_teams),
            'cash_revenue': cash_revenue,
            'upi_revenue': upi_revenue,
            'total_revenue': total_revenue
        }
        
        return render_template('admin.html', teams=teams, payment_stats=payment_stats)

    @app.route('/admin/update_status', methods=['POST'])
    def update_team_status():
        """Update team match status"""
        try:
            team_id = request.json.get('team_id')
            new_status = request.json.get('status')
            
            result = execute_query('UPDATE teams SET match_status = %s WHERE team_id = %s', 
                                  (new_status, team_id))
            
            # Invalidate cache after data change
            invalidate_cache()
            
            if result:
                # Emit real-time update
                socketio.emit('status_updated', {
                    'team_id': team_id,
                    'status': new_status
                })
                return jsonify({'success': True})
            
            return jsonify({'success': False, 'message': 'Database error'})
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/admin/delete_team', methods=['POST'])
    def delete_team():
        """Delete a single team"""
        try:
            team_id = request.json.get('team_id')
            
            # Get team details before deletion for notification
            team = execute_query('SELECT * FROM teams WHERE team_id = %s', (team_id,), fetch_one=True)
            
            if not team:
                return jsonify({'success': False, 'message': 'Team not found'})
            
            # Delete QR code file if exists
            if team.get('qr_code_path'):
                qr_path = team['qr_code_path']
                if os.path.exists(qr_path):
                    try:
                        os.remove(qr_path)
                        print(f"✅ Deleted QR code: {qr_path}")
                    except Exception as e:
                        print(f"⚠️ Could not delete QR code {qr_path}: {e}")
            
            # Delete from database
            result = execute_query('DELETE FROM teams WHERE team_id = %s', (team_id,))
            
            # Invalidate cache after data change
            invalidate_cache()
            
            if result:
                # Emit real-time update
                socketio.emit('team_deleted', {
                    'team_id': team_id,
                    'player1_name': team.get('player1_name', ''),
                    'player2_name': team.get('player2_name', '')
                })
                
                print(f"✅ Team {team_id} deleted successfully")
                return jsonify({'success': True, 'message': f'Team {team_id} deleted successfully'})
            
            return jsonify({'success': False, 'message': 'Database error'})
            
        except Exception as e:
            print(f"❌ Error deleting team: {e}")
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/admin/delete_all_teams', methods=['POST'])
    def delete_all_teams():
        """Delete all teams"""
        try:
            # Get count of teams before deletion
            count_result = execute_query('SELECT COUNT(*) as count FROM teams', fetch_one=True)
            team_count = count_result['count'] if count_result else 0
            
            if team_count == 0:
                return jsonify({'success': False, 'message': 'No teams to delete'})
            
            # Get all QR code paths before deletion
            teams = execute_query('SELECT qr_code_path FROM teams WHERE qr_code_path IS NOT NULL', fetch_all=True)
            
            # Delete all QR code files
            deleted_files = 0
            if teams:
                for team in teams:
                    qr_path = team.get('qr_code_path')
                    if qr_path and os.path.exists(qr_path):
                        try:
                            os.remove(qr_path)
                            deleted_files += 1
                        except Exception as e:
                            print(f"⚠️ Could not delete QR code {qr_path}: {e}")
            
            # Delete all teams from database
            result = execute_query('DELETE FROM teams')
            
            # Reset auto-increment counter
            try:
                if 'postgresql' in str(execute_query).lower():
                    execute_query('ALTER SEQUENCE teams_id_seq RESTART WITH 1')
                else:
                    execute_query("DELETE FROM sqlite_sequence WHERE name='teams'")
            except Exception as e:
                print(f"⚠️ Could not reset sequence: {e}")
            
            # Invalidate cache after data change
            invalidate_cache()
            
            if result:
                # Emit real-time update
                socketio.emit('all_teams_deleted', {
                    'count': team_count,
                    'files_deleted': deleted_files
                })
                
                print(f"✅ All {team_count} teams deleted successfully, {deleted_files} QR files removed")
                return jsonify({
                    'success': True, 
                    'message': f'All {team_count} teams deleted successfully',
                    'teams_deleted': team_count,
                    'files_deleted': deleted_files
                })
            
            return jsonify({'success': False, 'message': 'Database error'})
            
        except Exception as e:
            print(f"❌ Error deleting all teams: {e}")
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/admin/resend_email', methods=['POST'])
    def resend_email():
        """Resend QR code email for a team"""
        try:
            team_id = request.json.get('team_id')
            
            # Get team details
            team = execute_query('SELECT * FROM teams WHERE team_id = %s', (team_id,), fetch_one=True)
            
            if not team:
                return jsonify({'success': False, 'message': 'Team not found'})
            
            if not team.get('email'):
                return jsonify({'success': False, 'message': 'No email address for this team'})
            
            # Send QR code email
            if team.get('qr_code_path') and os.path.exists(team['qr_code_path']):
                success = send_qr_email(
                    team['email'],
                    team['team_id'],
                    team['player1_name'],
                    team['player2_name'],
                    team['qr_code_path'],
                    team.get('queue_number'),
                    team.get('group_id')
                )
                
                if success:
                    return jsonify({'success': True, 'message': 'Email sent successfully'})
                else:
                    return jsonify({'success': False, 'message': 'Failed to send email'})
            else:
                return jsonify({'success': False, 'message': 'QR code not found'})
            
        except Exception as e:
            print(f"❌ Error resending email: {e}")
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/api/teams')
    def get_teams():
        """API endpoint to get all teams from database"""
        # Try cache first
        cached_teams = get_cached_data('teams', 30)
        if cached_teams:
            return jsonify(cached_teams)
        
        teams = execute_query('SELECT * FROM teams ORDER BY created_at DESC LIMIT 100', fetch_all=True) or []
        
        # Convert datetime objects to strings and map field names for JSON serialization
        for team in teams:
            # Map database field names to what JavaScript expects
            team['status'] = team.get('match_status', 'waiting')
            team['registered_at'] = team.get('created_at')
            
            # Convert datetime objects to strings
            if team.get('created_at'):
                if not isinstance(team['created_at'], str):
                    team['created_at'] = team['created_at'].isoformat()
                    team['registered_at'] = team['created_at']
            if team.get('validated_at'):
                if not isinstance(team['validated_at'], str):
                    team['validated_at'] = team['validated_at'].isoformat()
            if team.get('goal_recorded_at'):
                if not isinstance(team['goal_recorded_at'], str):
                    team['goal_recorded_at'] = team['goal_recorded_at'].isoformat()
        
        # Cache the results
        set_cached_data('teams', teams)
        
        return jsonify(teams)

    @app.route('/api/stats')
    def get_stats():
        """API endpoint to get team statistics from database"""
        # Try cache first
        cached_stats = get_cached_data('stats', 30)
        if cached_stats:
            return jsonify(cached_stats)
        
        stats = {'total': 0, 'validated': 0, 'playing': 0, 'completed': 0}
        
        try:
            conn = get_db_connection()
            if conn:
                cur = get_cursor(conn)
                
                # Single optimized query
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN validation_status = 'Validated' THEN 1 END) as validated,
                        COUNT(CASE WHEN match_status = 'Playing' THEN 1 END) as playing,
                        COUNT(CASE WHEN match_status = 'Completed' THEN 1 END) as completed
                    FROM teams
                """)
                
                result = cur.fetchone()
                if result:
                    stats = {
                        'total': result[0] if result[0] else 0,
                        'validated': result[1] if result[1] else 0,
                        'playing': result[2] if result[2] else 0,
                        'completed': result[3] if result[3] else 0
                    }
                
                cur.close()
                conn.close()
                
                # Cache the results
                set_cached_data('stats', stats)
                
        except Exception as e:
            print(f"Stats query error: {e}")
        
        return jsonify(stats)

    @app.route('/admin/export', methods=['GET'])
    def export_data():
        """Export teams data to Excel"""
        try:
            teams = execute_query('SELECT * FROM teams ORDER BY created_at DESC', fetch_all=True) or []
            
            # Create Excel file
            wb = Workbook()
            ws = wb.active
            ws.title = "Teams"
            
            # Headers
            headers = ['Team ID', 'Player 1 Name', 'Player 1 PID', 'Player 1 Phone', 'Player 2 Name', 'Player 2 PID', 'Player 2 Phone',
                      'Email', 'Payment Status', 'Payment Amount', 'Payment Method', 'QR Code Path', 
                      'Validation Status', 'Match Status', 'Goal Time', 'Goal Recorded At', 
                      'Created At', 'Validated At']
            ws.append(headers)
            
            # Data
            for team in teams:
                row = [
                    team.get('team_id', ''),
                    team.get('player1_name', ''),
                    team.get('player1_pid', ''),
                    team.get('player1_phone', ''),
                    team.get('player2_name', ''),
                    team.get('player2_pid', ''),
                    team.get('player2_phone', ''),
                    team.get('email', ''),
                    team.get('payment_status', ''),
                    team.get('payment_amount', ''),
                    team.get('payment_method', ''),
                    team.get('qr_code_path', ''),
                    team.get('validation_status', ''),
                    team.get('match_status', ''),
                    team.get('goal_time', ''),
                    team.get('goal_recorded_at', ''),
                    team.get('created_at', ''),
                    team.get('validated_at', '')
                ]
                ws.append(row)
            
            # Add Payment Summary Sheet
            ws_summary = wb.create_sheet("Payment Summary")
            
            # Calculate payment stats
            cash_teams = [t for t in teams if t.get('payment_method') == 'Cash']
            upi_teams = [t for t in teams if t.get('payment_method') == 'UPI']
            cash_revenue = sum([float(t.get('payment_amount', 0) or 0) for t in cash_teams])
            upi_revenue = sum([float(t.get('payment_amount', 0) or 0) for t in upi_teams])
            total_revenue = sum([float(t.get('payment_amount', 0) or 0) for t in teams])
            
            # Payment summary data
            summary_data = [
                ['=== PAYMENT METHOD SUMMARY ===', '', ''],
                ['Payment Method', 'Teams Count', 'Total Revenue (₹)'],
                ['💵 Cash', len(cash_teams), cash_revenue],
                ['📱 UPI', len(upi_teams), upi_revenue],
                ['📊 Total', len(teams), total_revenue],
                ['', '', ''],
                ['=== CASH BREAKDOWN ===', '', ''],
                ['Team ID', 'Players', 'Amount (₹)']
            ]
            
            for row in summary_data:
                ws_summary.append(row)
            
            # Add cash details
            for team in cash_teams:
                ws_summary.append([
                    team.get('team_id', ''),
                    f"{team.get('player1_name', '')} & {team.get('player2_name', '')}",
                    float(team.get('payment_amount', 0) or 0)
                ])
            
            # Add UPI section
            ws_summary.append(['', '', ''])
            ws_summary.append(['=== UPI BREAKDOWN ===', '', ''])
            ws_summary.append(['Team ID', 'Players', 'Amount (₹)'])
            
            for team in upi_teams:
                ws_summary.append([
                    team.get('team_id', ''),
                    f"{team.get('player1_name', '')} & {team.get('player2_name', '')}",
                    float(team.get('payment_amount', 0) or 0)
                ])
            
            # Save to file
            filename = f'teams_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            wb.save(filename)
            
            return send_file(filename, as_attachment=True, download_name=filename)
            
        except Exception as e:
            print(f"❌ Export error: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/admin/export_stats', methods=['GET'])
    def export_stats():
        """Export detailed statistics to Excel"""
        try:
            teams = execute_query('SELECT * FROM teams ORDER BY created_at DESC', fetch_all=True) or []
            
            # Create Excel file with multiple sheets
            wb = Workbook()
            
            # Teams sheet
            ws_teams = wb.active
            ws_teams.title = "Teams"
            headers = ['Team ID', 'Player 1 Name', 'Player 1 PID', 'Player 1 Phone', 'Player 2 Name', 'Player 2 PID', 'Player 2 Phone',
                      'Email', 'Payment Status', 'Payment Amount', 'Payment Method', 'Validation Status', 
                      'Match Status', 'Goal Time', 'Goal Recorded At', 'Created At', 'Validated At']
            ws_teams.append(headers)
            
            for team in teams:
                row = [
                    team.get('team_id', ''),
                    team.get('player1_name', ''),
                    team.get('player1_pid', ''),
                    team.get('player1_phone', ''),
                    team.get('player2_name', ''),
                    team.get('player2_pid', ''),
                    team.get('player2_phone', ''),
                    team.get('email', ''),
                    team.get('payment_status', ''),
                    team.get('payment_amount', ''),
                    team.get('payment_method', ''),
                    team.get('validation_status', ''),
                    team.get('match_status', ''),
                    team.get('goal_time', ''),
                    team.get('goal_recorded_at', ''),
                    team.get('created_at', ''),
                    team.get('validated_at', '')
                ]
                ws_teams.append(row)
            
            # Statistics sheet
            ws_stats = wb.create_sheet("Statistics")
            
            # Calculate basic stats
            total_teams = len(teams)
            validated_teams = len([t for t in teams if t.get('validation_status') == 'Validated'])
            playing_teams = len([t for t in teams if t.get('match_status') == 'Playing'])
            completed_teams = len([t for t in teams if t.get('match_status') == 'Completed'])
            paid_teams = len([t for t in teams if t.get('payment_status') == 'Paid'])
            
            # Calculate payment method stats
            cash_teams = [t for t in teams if t.get('payment_method') == 'Cash']
            upi_teams = [t for t in teams if t.get('payment_method') == 'UPI']
            no_method_teams = [t for t in teams if not t.get('payment_method')]
            
            # Calculate revenue by payment method
            cash_revenue = sum([float(t.get('payment_amount', 0) or 0) for t in cash_teams])
            upi_revenue = sum([float(t.get('payment_amount', 0) or 0) for t in upi_teams])
            total_revenue = sum([float(t.get('payment_amount', 0) or 0) for t in teams])
            
            # Calculate paid amounts by method
            paid_cash_teams = [t for t in cash_teams if t.get('payment_status') == 'Paid']
            paid_upi_teams = [t for t in upi_teams if t.get('payment_status') == 'Paid']
            paid_cash_revenue = sum([float(t.get('payment_amount', 0) or 0) for t in paid_cash_teams])
            paid_upi_revenue = sum([float(t.get('payment_amount', 0) or 0) for t in paid_upi_teams])
            
            # Add stats to sheet
            stats_data = [
                ['=== TEAM STATISTICS ===', '', ''],
                ['Statistic', 'Count', 'Percentage'],
                ['Total Teams', total_teams, '100%'],
                ['Validated Teams', validated_teams, f'{(validated_teams/total_teams*100):.1f}%' if total_teams > 0 else '0%'],
                ['Playing Teams', playing_teams, f'{(playing_teams/total_teams*100):.1f}%' if total_teams > 0 else '0%'],
                ['Completed Teams', completed_teams, f'{(completed_teams/total_teams*100):.1f}%' if total_teams > 0 else '0%'],
                ['Paid Teams', paid_teams, f'{(paid_teams/total_teams*100):.1f}%' if total_teams > 0 else '0%'],
                ['', '', ''],
                ['=== PAYMENT METHOD BREAKDOWN ===', '', ''],
                ['Payment Method', 'Teams', 'Revenue (₹)'],
                ['💵 Cash', len(cash_teams), f'{cash_revenue:.2f}'],
                ['📱 UPI', len(upi_teams), f'{upi_revenue:.2f}'],
                ['❌ No Method', len(no_method_teams), '0.00'],
                ['📊 Total', total_teams, f'{total_revenue:.2f}'],
                ['', '', ''],
                ['=== PAID AMOUNTS BY METHOD ===', '', ''],
                ['Payment Method', 'Paid Teams', 'Paid Revenue (₹)'],
                ['💵 Cash (Paid)', len(paid_cash_teams), f'{paid_cash_revenue:.2f}'],
                ['📱 UPI (Paid)', len(paid_upi_teams), f'{paid_upi_revenue:.2f}'],
                ['💰 Total Paid', len(paid_cash_teams) + len(paid_upi_teams), f'{paid_cash_revenue + paid_upi_revenue:.2f}'],
                ['', '', ''],
                ['=== PENDING AMOUNTS ===', '', ''],
                ['Payment Method', 'Pending Teams', 'Pending Revenue (₹)'],
                ['💵 Cash (Pending)', len(cash_teams) - len(paid_cash_teams), f'{cash_revenue - paid_cash_revenue:.2f}'],
                ['📱 UPI (Pending)', len(upi_teams) - len(paid_upi_teams), f'{upi_revenue - paid_upi_revenue:.2f}'],
                ['⏳ Total Pending', (len(cash_teams) - len(paid_cash_teams)) + (len(upi_teams) - len(paid_upi_teams)), f'{(cash_revenue - paid_cash_revenue) + (upi_revenue - paid_upi_revenue):.2f}'],
                ['', '', ''],
                ['=== EXPORT INFO ===', '', ''],
                ['Export Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ''],
                ['Export Time', datetime.now().strftime('%H:%M:%S'), ''],
                ['Total Records', total_teams, '']
            ]
            
            for row in stats_data:
                ws_stats.append(row)
            
            # Payment Summary Sheet
            ws_payment = wb.create_sheet("Payment Summary")
            
            # Create detailed payment breakdown
            payment_headers = ['Team ID', 'Player Names', 'Payment Method', 'Amount (₹)', 'Status', 'Date']
            ws_payment.append(payment_headers)
            
            # Add cash payments
            ws_payment.append(['=== CASH PAYMENTS ===', '', '', '', '', ''])
            for team in cash_teams:
                ws_payment.append([
                    team.get('team_id', ''),
                    f"{team.get('player1_name', '')} & {team.get('player2_name', '')}",
                    '💵 Cash',
                    float(team.get('payment_amount', 0) or 0),
                    team.get('payment_status', ''),
                    team.get('created_at', '')
                ])
            
            # Add UPI payments
            ws_payment.append(['', '', '', '', '', ''])
            ws_payment.append(['=== UPI PAYMENTS ===', '', '', '', '', ''])
            for team in upi_teams:
                ws_payment.append([
                    team.get('team_id', ''),
                    f"{team.get('player1_name', '')} & {team.get('player2_name', '')}",
                    '📱 UPI',
                    float(team.get('payment_amount', 0) or 0),
                    team.get('payment_status', ''),
                    team.get('created_at', '')
                ])
            
            # Add totals
            ws_payment.append(['', '', '', '', '', ''])
            ws_payment.append(['=== TOTALS ===', '', '', '', '', ''])
            ws_payment.append(['Cash Total', '', '', cash_revenue, '', ''])
            ws_payment.append(['UPI Total', '', '', upi_revenue, '', ''])
            ws_payment.append(['Grand Total', '', '', total_revenue, '', ''])
            
            # Leaderboard Sheet
            ws_leaderboard = wb.create_sheet("Leaderboard")
            
            # Get teams with goal times sorted by time
            teams_with_times = [t for t in teams if t.get('goal_time')]
            teams_with_times.sort(key=lambda x: float(x.get('goal_time', 999999)))
            
            # Leaderboard headers
            leaderboard_headers = ['Rank', 'Team ID', 'Player 1', 'Player 1 Phone', 'Player 2', 'Player 2 Phone', 'Goal Time (s)', 'Recorded At']
            ws_leaderboard.append(leaderboard_headers)
            
            # Add leaderboard data
            for i, team in enumerate(teams_with_times):
                rank = i + 1
                medal = '🥇' if rank == 1 else '🥈' if rank == 2 else '🥉' if rank == 3 else str(rank)
                ws_leaderboard.append([
                    f"{medal} {rank}",
                    team.get('team_id', ''),
                    team.get('player1_name', ''),
                    team.get('player1_phone', ''),
                    team.get('player2_name', ''),
                    team.get('player2_phone', ''),
                    float(team.get('goal_time', 0)),
                    team.get('goal_recorded_at', '')
                ])
            
            if not teams_with_times:
                ws_leaderboard.append(['No goal times recorded yet', '', '', '', '', ''])
            
            # Save to file
            filename = f'teams_stats_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            wb.save(filename)
            
            return send_file(filename, as_attachment=True, download_name=filename)
            
        except Exception as e:
            print(f"❌ Stats export error: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/test_playing_team', methods=['POST'])
    def create_test_playing_team():
        """Create a test team for testing purposes"""
        try:
            import random
            team_id = f"TEST{random.randint(100, 999)}"
            
            # Insert test team
            execute_query('''
                INSERT INTO teams (team_id, player1_name, player2_name, email, 
                                 validation_status, match_status, queue_number, group_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (team_id, f"Player{random.randint(1,99)}", f"Player{random.randint(1,99)}", 
                  "test@example.com", "Validated", "Playing", random.randint(1,10), 1))
            
            return jsonify({
                'success': True,
                'team': {
                    'team_id': team_id,
                    'player1_name': f"Player{random.randint(1,99)}",
                    'player2_name': f"Player{random.randint(1,99)}"
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/api/regenerate-passwords', methods=['POST'])
    @login_required('Admin')
    def regenerate_passwords():
        """Regenerate all page passwords and send new email"""
        try:
            # Delete existing password file
            if os.path.exists(PASSWORD_FILE):
                os.remove(PASSWORD_FILE)
                print("🗑️ Deleted existing password file", flush=True)
            
            # Generate new passwords
            global PAGE_PASSWORDS
            PAGE_PASSWORDS, _ = load_or_generate_passwords()
            
            # Send email with new passwords
            if send_all_passwords_email(newly_generated=True):
                return jsonify({
                    'success': True, 
                    'message': f'New passwords generated and sent to {ADMIN_EMAIL}',
                    'passwords': PAGE_PASSWORDS
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': 'Passwords generated but email sending failed'
                })
                
        except Exception as e:
            print(f"❌ Error regenerating passwords: {e}", flush=True)
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/feedback')
    def feedback_page():
        """Feedback form page"""
        team_id = request.args.get('team_id', '')
        return render_template('feedback.html', team_id=team_id)

    @app.route('/feedback', methods=['POST'])
    def submit_feedback():
        """Handle feedback form submission"""
        try:
            # Get form data
            team_id = request.form.get('team_id')
            email = request.form.get('email')
            overall_rating = request.form.get('overall_rating')
            registration_process = request.form.get('registration_process')
            competition_organization = request.form.get('competition_organization')
            venue_facilities = request.form.get('venue_facilities')
            staff_support = request.form.get('staff_support')
            what_went_well = request.form.get('what_went_well', '')
            improvements = request.form.get('improvements', '')
            additional_comments = request.form.get('additional_comments', '')
            participate_again = request.form.get('participate_again')
            recommend_others = request.form.get('recommend_others')
            
            # Store feedback in database (create table if not exists)
            try:
                if USE_POSTGRES:
                    execute_query('''
                        CREATE TABLE IF NOT EXISTS feedback (
                            id SERIAL PRIMARY KEY,
                            team_id VARCHAR(50),
                            email VARCHAR(255),
                            overall_rating INTEGER,
                            registration_process INTEGER,
                            competition_organization INTEGER,
                            venue_facilities INTEGER,
                            staff_support INTEGER,
                            what_went_well TEXT,
                            improvements TEXT,
                            additional_comments TEXT,
                            participate_again VARCHAR(50),
                            recommend_others VARCHAR(50),
                            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                else:
                    execute_query('''
                        CREATE TABLE IF NOT EXISTS feedback (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            team_id TEXT,
                            email TEXT,
                            overall_rating INTEGER,
                            registration_process INTEGER,
                            competition_organization INTEGER,
                            venue_facilities INTEGER,
                            staff_support INTEGER,
                            what_went_well TEXT,
                            improvements TEXT,
                            additional_comments TEXT,
                            participate_again TEXT,
                            recommend_others TEXT,
                            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
            except Exception as e:
                print(f"Error creating feedback table: {e}", flush=True)
            
            # Insert feedback
            execute_query('''
                INSERT INTO feedback (team_id, email, overall_rating, registration_process, 
                                    competition_organization, venue_facilities, staff_support,
                                    what_went_well, improvements, additional_comments,
                                    participate_again, recommend_others)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (team_id, email, overall_rating, registration_process, competition_organization,
                  venue_facilities, staff_support, what_went_well, improvements, 
                  additional_comments, participate_again, recommend_others))
            
            # Send thank you email
            if email and app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
                try:
                    send_feedback_thank_you_email(email, team_id)
                except Exception as e:
                    print(f"Error sending thank you email: {e}", flush=True)
            
            flash('🚀 Feedback transmitted successfully! Thank you for helping us improve.', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            print(f"Error submitting feedback: {e}", flush=True)
            flash('Error submitting feedback. Please try again.', 'error')
            return render_template('feedback.html', team_id=request.form.get('team_id', ''))

    def send_feedback_thank_you_email(email, team_id):
        """Send thank you email after feedback submission"""
        try:
            msg = MIMEMultipart('related')
            msg['Subject'] = f'TEAM RAW - Thank You for Your Feedback!'
            msg['From'] = app.config['MAIL_USERNAME']
            msg['To'] = email
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: 'Arial', sans-serif; line-height: 1.6; color: #333333; background: #f8f9fa; margin: 0; padding: 0; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background: white; }}
                    .header {{ background: linear-gradient(135deg, #1e5aa8 0%, #c41e3a 100%); color: white; padding: 25px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .logo {{ width: 70px; height: 70px; border-radius: 10px; margin-bottom: 10px; border: 2px solid white; }}
                    .content {{ background: white; padding: 25px; border-radius: 0 0 10px 10px; border: 1px solid #e0e0e0; }}
                    .thank-you {{ background: #f0f4ff; padding: 20px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #1e5aa8; text-align: center; }}
                    .social-links {{ text-align: center; margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 10px; }}
                    .social-btn {{ display: inline-block; margin: 0 8px; padding: 10px 20px; background: linear-gradient(45deg, #1e5aa8, #c41e3a); color: white; text-decoration: none; border-radius: 20px; font-weight: bold; font-size: 13px; }}
                    .footer {{ text-align: center; margin-top: 20px; color: #666666; font-size: 12px; }}
                    .team-title {{ color: #1e5aa8; font-weight: bold; font-size: 24px; margin: 10px 0; }}
                    .highlight-blue {{ color: #1e5aa8; font-weight: bold; }}
                    .highlight-red {{ color: #c41e3a; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="cid:team_logo" alt="TEAM RAW Logo" class="logo">
                        <div class="team-title"><span style="color: #87ceeb;">TEAM</span> <span style="color: #ffb6c1;">RAW</span></div>
                        <div style="font-size: 16px; margin: 8px 0;">Thank You!</div>
                    </div>
                    <div class="content">
                        <div class="thank-you">
                            <h2 style="color: #1e5aa8; font-size: 20px; margin-bottom: 15px;">🚀 Feedback Received!</h2>
                            <p style="font-size: 14px; color: #333333; line-height: 1.6; margin: 12px 0;">
                                Thank you for taking the time to provide feedback about your robotics competition experience.
                            </p>
                            <p style="color: #c41e3a; font-size: 14px; margin: 12px 0;">
                                <strong>Team {team_id}</strong> - Your input helps us improve future competitions!
                            </p>
                        </div>
                        
                        <div style="background: #fff5f5; padding: 20px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #c41e3a;">
                            <h3 style="color: #c41e3a; font-size: 16px; margin-bottom: 12px;">🔧 What Happens Next?</h3>
                            <ul style="color: #333333; font-size: 13px; line-height: 1.6; margin: 0; padding-left: 20px;">
                                <li><strong>Review:</strong> Your feedback will be analyzed by our team</li>
                                <li><strong>Improvements:</strong> We'll use your suggestions for future events</li>
                                <li><strong>Updates:</strong> You'll hear about upcoming competitions</li>
                                <li><strong>Recognition:</strong> Look out for participant rewards</li>
                            </ul>
                        </div>
                        
                        <div class="social-links">
                            <h3 style="color: #1e5aa8; margin-bottom: 12px; font-size: 16px;">🌐 Follow TEAM RAW</h3>
                            <a href="https://www.instagram.com/teamraw_robotics" class="social-btn">
                                📸 Instagram
                            </a>
                            <a href="https://www.linkedin.com/company/team-raw-robotics" class="social-btn" style="background: linear-gradient(45deg, #0077B5, #3399ff);">
                                💼 LinkedIn
                            </a>
                            <p style="margin-top: 15px; color: #ffffff; font-size: 14px;">
                                Follow us for robotics updates, competition announcements, and behind-the-scenes content!
                            </p>
                        </div>
                        
                        <p style="text-align: center; color: #3399ff; font-size: 20px; font-weight: bold; margin: 30px 0;">
                            <span style="color: #ff3366;">THANK YOU</span> FOR BEING PART OF THE ROBOTICS REVOLUTION! 🚀
                        </p>
                    </div>
                    <div class="footer">
                        <p style="color: #adb5bd; font-size: 14px;">TEAM RAW Robotics | Advanced Competition Management</p>
                        <p style="color: #3399ff; font-size: 12px;">Your feedback drives our innovation</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create alternative container
            msg_alternative = MIMEMultipart('alternative')
            msg.attach(msg_alternative)
            
            # Add HTML part
            html_part = MIMEText(html_body, 'html')
            msg_alternative.attach(html_part)
            
            # Attach TEAM RAW logo
            logo_path = 'static/images/RawLogo.jpeg'
            if os.path.exists(logo_path):
                with open(logo_path, 'rb') as f:
                    logo_image_data = f.read()
                    logo_image = MIMEImage(logo_image_data)
                    logo_image.add_header('Content-ID', '<team_logo>')
                    logo_image.add_header('Content-Disposition', 'inline', filename='team_raw_logo.jpeg')
                    msg.attach(logo_image)
            
            # Send email
            server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Thank you email sent to {email}", flush=True)
            return True
            
        except Exception as e:
            print(f"❌ Failed to send thank you email: {e}", flush=True)
            return False

    def send_feedback_request_email(email, team_id, player1_name, player2_name):
        """Send feedback request email after game completion"""
        try:
            msg = MIMEMultipart('related')
            msg['Subject'] = f'TEAM RAW - Mission Complete! Share Your Experience'
            msg['From'] = app.config['MAIL_USERNAME']
            msg['To'] = email
            
            # Google Form URL with pre-filled team details
            google_form_url = f"https://docs.google.com/forms/d/e/{GOOGLE_FORM_ID}/viewform?usp=pp_url&{GOOGLE_FORM_TEAM_ID_FIELD}={team_id}&{GOOGLE_FORM_PLAYER1_FIELD}={player1_name}&{GOOGLE_FORM_PLAYER2_FIELD}={player2_name}"
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: 'Arial', sans-serif; line-height: 1.6; color: #333333; background: #f8f9fa; margin: 0; padding: 0; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background: white; }}
                    .header {{ background: linear-gradient(135deg, #1e5aa8 0%, #c41e3a 100%); color: white; padding: 25px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .logo {{ width: 70px; height: 70px; border-radius: 10px; margin-bottom: 10px; border: 2px solid white; }}
                    .content {{ background: white; padding: 25px; border-radius: 0 0 10px 10px; border: 1px solid #e0e0e0; }}
                    .completion {{ background: #f0f4ff; padding: 20px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #1e5aa8; text-align: center; }}
                    .feedback-section {{ background: #fff5f5; padding: 20px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #c41e3a; text-align: center; }}
                    .feedback-btn {{ display: inline-block; padding: 15px 30px; background: linear-gradient(45deg, #1e5aa8, #c41e3a); color: white; text-decoration: none; border-radius: 25px; font-weight: bold; font-size: 16px; margin: 12px 0; }}
                    .social-links {{ text-align: center; margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 10px; }}
                    .social-btn {{ display: inline-block; margin: 0 8px; padding: 10px 20px; background: linear-gradient(45deg, #1e5aa8, #c41e3a); color: white; text-decoration: none; border-radius: 20px; font-weight: bold; font-size: 13px; }}
                    .footer {{ text-align: center; margin-top: 20px; color: #666666; font-size: 12px; }}
                    .team-title {{ color: #1e5aa8; font-weight: bold; font-size: 24px; margin: 10px 0; }}
                    .instructions {{ background: #f0f4ff; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #1e5aa8; }}
                    .highlight-blue {{ color: #1e5aa8; font-weight: bold; }}
                    .highlight-red {{ color: #c41e3a; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="cid:team_logo" alt="TEAM RAW Logo" class="logo">
                        <div class="team-title"><span style="color: #87ceeb;">TEAM</span> <span style="color: #ffb6c1;">RAW</span></div>
                        <div style="font-size: 16px; margin: 8px 0;">Competition Complete!</div>
                    </div>
                    <div class="content">
                        <div class="completion">
                            <h2 style="color: #1e5aa8; font-size: 20px; margin-bottom: 15px;">🏆 Congratulations!</h2>
                            <p style="font-size: 14px; color: #333333; line-height: 1.6; margin: 12px 0;">
                                <strong>Team {team_id}</strong> has successfully completed the robotics competition!
                            </p>
                            <p style="color: #c41e3a; font-size: 14px; margin: 12px 0;">
                                <strong class="highlight-blue">{player1_name}</strong> & <strong class="highlight-red">{player2_name}</strong>
                            </p>
                            <p style="color: #1e5aa8; font-size: 14px; margin: 12px 0;">
                                🚀 Your performance has been recorded!
                            </p>
                        </div>
                        
                        <div class="feedback-section">
                            <h3 style="color: #c41e3a; margin-bottom: 12px; font-size: 18px;">📝 Share Your Experience</h3>
                            <p style="color: #333333; margin-bottom: 15px; font-size: 14px; line-height: 1.6;">
                                Help us improve future competitions by sharing your feedback. It only takes 3-5 minutes!
                            </p>
                            
                            <a href="{google_form_url}" class="feedback-btn" target="_blank">
                                📝 Complete Feedback Form
                            </a>
                            
                            <div class="instructions">
                                <h4 style="color: #3399ff; margin-bottom: 15px; font-size: 18px;">📋 FEEDBACK PROTOCOL:</h4>
                                <ul style="color: #ffffff; text-align: left; margin: 0; padding-left: 20px; font-size: 15px; line-height: 1.8;">
                                    <li>⚡ <strong>Quick Access:</strong> Form opens in new window/tab</li>
                                    <li>🎯 <strong>Pre-filled Data:</strong> Your team details are already entered</li>
                                    <li>⭐ <strong>Rate Experience:</strong> Evaluate different competition aspects</li>
                                    <li>💡 <strong>Share Ideas:</strong> Provide improvement suggestions</li>
                                    <li>🕐 <strong>Time Required:</strong> Only 3-5 minutes to complete</li>
                                </ul>
                            </div>
                            
                            <p style="font-size: 14px; color: #adb5bd; margin-top: 15px;">
                                🔒 Your feedback is secure and confidential - it helps drive our innovation
                            </p>
                        </div>
                        
                        <div class="social-links">
                            <h4 style="color: #3399ff; margin-bottom: 15px; font-size: 18px;">🌐 CONNECT WITH TEAM RAW</h4>
                            <a href="https://www.instagram.com/teamraw_robotics" class="social-btn" style="background: linear-gradient(45deg, #E4405F, #ff3366);">
                                📸 Instagram
                            </a>
                            <a href="https://www.linkedin.com/company/team-raw-robotics" class="social-btn" style="background: linear-gradient(45deg, #0077B5, #3399ff);">
                                💼 LinkedIn
                            </a>
                            <p style="margin-top: 15px; color: #ffffff; font-size: 14px;">
                                Follow us for competition results, robotics insights, and future event announcements!
                            </p>
                        </div>
                        
                        <p style="text-align: center; color: #3399ff; font-size: 20px; font-weight: bold; margin: 30px 0;">
                            <span style="color: #ff3366;">THANK YOU</span> FOR PARTICIPATING IN THE ROBOTICS REVOLUTION! 🏆
                        </p>
                    </div>
                    <div class="footer">
                        <p style="color: #adb5bd; font-size: 14px;">TEAM RAW Robotics | Advanced Competition Management</p>
                        <p style="color: #3399ff; font-size: 12px;">Building the future of robotics competitions</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Create alternative container
            msg_alternative = MIMEMultipart('alternative')
            msg.attach(msg_alternative)
            
            # Add HTML part
            html_part = MIMEText(html_body, 'html')
            msg_alternative.attach(html_part)
            
            # Attach TEAM RAW logo
            logo_path = 'static/images/RawLogo.jpeg'
            if os.path.exists(logo_path):
                with open(logo_path, 'rb') as f:
                    logo_image_data = f.read()
                    logo_image = MIMEImage(logo_image_data)
                    logo_image.add_header('Content-ID', '<team_logo>')
                    logo_image.add_header('Content-Disposition', 'inline', filename='team_raw_logo.jpeg')
                    msg.attach(logo_image)
            
            # Send email
            server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Feedback request email sent to {email}", flush=True)
            return True
            
        except Exception as e:
            print(f"❌ Failed to send feedback request email: {e}", flush=True)
            return False

    @app.route('/admin/feedback-config')
    @login_required('Admin')
    def feedback_config():
        """Admin page to configure Google Form settings"""
        return render_template('feedback_config.html', 
                             form_id=GOOGLE_FORM_ID,
                             team_field=GOOGLE_FORM_TEAM_ID_FIELD,
                             player1_field=GOOGLE_FORM_PLAYER1_FIELD,
                             player2_field=GOOGLE_FORM_PLAYER2_FIELD)

    @app.route('/admin/feedback-config', methods=['POST'])
    @login_required('Admin')
    def update_feedback_config():
        """Update Google Form configuration"""
        try:
            global GOOGLE_FORM_ID, GOOGLE_FORM_TEAM_ID_FIELD, GOOGLE_FORM_PLAYER1_FIELD, GOOGLE_FORM_PLAYER2_FIELD
            
            GOOGLE_FORM_ID = request.form.get('form_id', GOOGLE_FORM_ID)
            GOOGLE_FORM_TEAM_ID_FIELD = request.form.get('team_field', GOOGLE_FORM_TEAM_ID_FIELD)
            GOOGLE_FORM_PLAYER1_FIELD = request.form.get('player1_field', GOOGLE_FORM_PLAYER1_FIELD)
            GOOGLE_FORM_PLAYER2_FIELD = request.form.get('player2_field', GOOGLE_FORM_PLAYER2_FIELD)
            
            flash('✅ Google Form configuration updated successfully!', 'success')
            return redirect(url_for('feedback_config'))
            
        except Exception as e:
            flash(f'❌ Error updating configuration: {str(e)}', 'error')
            return redirect(url_for('feedback_config'))

    @app.route('/api/clear-cache', methods=['POST'])
    def clear_cache_endpoint():
        """API endpoint to clear all cache"""
        try:
            invalidate_cache()
            return jsonify({'success': True, 'message': 'Cache cleared successfully'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    # SocketIO events
    @socketio.on('connect')
    def handle_connect():
        print('Client connected', flush=True)

    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected', flush=True)

    def get_local_ip():
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    # Initialize database and Excel for ngrok
    print("=== Initializing MatchPulse Ngrok Edition ===")
    init_database()
    init_excel()
    
    # Test database connection
    test_conn = get_db_connection()
    if test_conn:
        print("✅ Database connection test successful")
        test_conn.close()
    else:
        print("❌ Database connection test failed")
    
    print("✅ MatchPulse Ngrok Edition initialized successfully")

    if __name__ == '__main__':
        # Get network info
        local_ip = get_local_ip()
        port = int(PORT)
        
        print("=" * 70)
        print("🏆 MATCHPULSE NGROK EDITION")
        print("=" * 70)
        print(f"🖥️  Local: http://localhost:{port}")
        print(f"📱 Network: http://{local_ip}:{port}")
        print()
        print("🌐 For ngrok mobile access:")
        print("   1. Keep this server running")
        print("   2. In another terminal: ngrok http 5000")
        print("   3. Use the ngrok HTTPS URL on mobile")
        print()
        print("📱 Ngrok optimizations:")
        print("   ✅ SQLite database for simplicity")
        print("   ✅ Mobile-friendly QR scanner")
        print("   ✅ HTTPS camera support")
        print("   ✅ Real-time updates")
        print("   ✅ Touch-optimized interface")
        print("   ✅ Auto-reload templates")
        print("=" * 70)
        print("🚀 Starting ngrok-optimized server...")
        print("=" * 70)
        
        # Send passwords via email only if newly generated
        if passwords_newly_generated:
            print("📧 Sending NEW passwords to admin email...")
            if send_all_passwords_email(newly_generated=True):
                print(f"✅ NEW passwords sent to {ADMIN_EMAIL}")
            else:
                print(f"❌ Failed to send NEW passwords email")
        else:
            print(f"📋 Using existing passwords (no email sent)")
            print(f"💡 To regenerate passwords, delete the '{PASSWORD_FILE}' file and restart")
        
        print("=" * 70)
        
        # Run the app optimized for ngrok
        socketio.run(app, host='127.0.0.1', port=port, debug=False, allow_unsafe_werkzeug=True)

except Exception as e:
    print(f"❌ MatchPulse Ngrok Edition startup failed: {e}", flush=True)
    import traceback
    traceback.print_exc()
    print("❌ Application failed to start. Check logs above for details.")