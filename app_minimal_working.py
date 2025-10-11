#!/usr/bin/env python3
"""
Team Registration System - Main Application
QR Code-Based Team Registration, Validation, and Live Match Monitoring System
"""

import sys
import os

print("=== Starting Team Registration System ===")

try:
    # Load environment variables FIRST
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded")

    # Debug environment loading
    DATABASE_URL = os.environ.get('DATABASE_URL', 'NOT FOUND')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'NOT FOUND')
    PORT = os.environ.get('PORT', '5001')
    
    print(f"DATABASE_URL: {DATABASE_URL[:50]}...")
    print(f"SECRET_KEY: {'Found' if SECRET_KEY != 'NOT FOUND' else 'NOT FOUND'}")
    print(f"PORT: {PORT}")

    # Import Flask components
    from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
    from flask_socketio import SocketIO, emit
    print("✅ Flask imports successful")

    # Import database components
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
    import base64
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    print("✅ All imports successful", flush=True)

    # Create Flask app
    app = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEY if SECRET_KEY != 'NOT FOUND' else 'fallback-secret-key'

    # Email configuration
    app.config['MAIL_SERVER'] = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('SMTP_PORT', 587))
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = os.environ.get('SMTP_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('SMTP_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('SMTP_USERNAME')

    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

    # Excel file path and in-memory storage
    EXCEL_FILE = 'teams_backup.xlsx'
    teams_data = []

    print("✅ Flask app and SocketIO created", flush=True)

    # Database configuration
    USE_POSTGRES = DATABASE_URL.startswith('postgresql://') and POSTGRES_AVAILABLE
    print(f"✅ Database type: {'PostgreSQL' if USE_POSTGRES else 'SQLite'}", flush=True)

    # Encryption key
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key())
    cipher_suite = Fernet(ENCRYPTION_KEY)
    print("✅ Encryption configured", flush=True)

    # Excel file path
    EXCEL_FILE = 'teams_backup.xlsx'

    def get_db_connection():
        """Get database connection"""
        try:
            if USE_POSTGRES:
                # Handle Neon database URL with channel_binding parameter
                db_url = DATABASE_URL
                if 'channel_binding=require' in db_url:
                    db_url = db_url.replace('&channel_binding=require', '').replace('?channel_binding=require&', '?').replace('?channel_binding=require', '')
                
                conn = psycopg2.connect(db_url)
                return conn
            else:
                # Use SQLite as fallback
                db_path = DATABASE_URL.replace('sqlite:///', '') if DATABASE_URL.startswith('sqlite://') else 'teams.db'
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
                    result = dict(result)  # Convert SQLite Row to dict
            elif fetch_all:
                result = cur.fetchall()
                if result and not USE_POSTGRES:
                    result = [dict(row) for row in result]  # Convert SQLite Rows to dicts
            else:
                # For INSERT, UPDATE, DELETE operations, return True on success
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
                            player2_name VARCHAR(100) NOT NULL,
                            email VARCHAR(255),
                            payment_status VARCHAR(20) DEFAULT 'Pending',
                            payment_amount DECIMAL(10,2),
                            payment_method VARCHAR(50),
                            qr_code_path VARCHAR(200),
                            validation_status VARCHAR(20) DEFAULT 'Not Validated',
                            match_status VARCHAR(20) DEFAULT 'Waiting',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            validated_at TIMESTAMP
                        )
                    ''')
                    
                    # Add new columns if they don't exist (for existing databases)
                    try:
                        cur.execute('ALTER TABLE teams ADD COLUMN payment_amount DECIMAL(10,2)')
                        conn.commit()
                        print("✅ Added payment_amount column to existing table")
                    except Exception:
                        pass  # Column already exists
                        
                    try:
                        cur.execute('ALTER TABLE teams ADD COLUMN payment_method VARCHAR(50)')
                        conn.commit()
                        print("✅ Added payment_method column to existing table")
                    except Exception:
                        pass  # Column already exists
                else:
                    cur.execute('''
                        CREATE TABLE IF NOT EXISTS teams (
                            team_id TEXT PRIMARY KEY,
                            player1_name TEXT NOT NULL,
                            player2_name TEXT NOT NULL,
                            email TEXT,
                            payment_status TEXT DEFAULT 'Pending',
                            payment_amount REAL,
                            payment_method TEXT,
                            qr_code_path TEXT,
                            validation_status TEXT DEFAULT 'Not Validated',
                            match_status TEXT DEFAULT 'Waiting',
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            validated_at DATETIME
                        )
                    ''')
                conn.commit()
                cur.close()
                conn.close()
                print(f"✅ Database initialized successfully ({'PostgreSQL' if USE_POSTGRES else 'SQLite'})", flush=True)
            else:
                print("❌ Could not connect to database", flush=True)
        except Exception as e:
            print(f"❌ Database initialization error: {e}", flush=True)

    def init_excel():
        """Initialize Excel backup file"""
        try:
            if not os.path.exists(EXCEL_FILE):
                wb = Workbook()
                ws = wb.active
                ws.title = "Teams"
                headers = ['Team ID', 'Player 1 Name', 'Player 2 Name', 'Email', 'Payment Status', 
                          'QR Code Path', 'Validation Status', 'Match Status', 'Created At', 'Validated At']
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
            'timestamp': datetime.now().isoformat()
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

    def update_excel_backup(team_id, player1_name, player2_name, payment_status, qr_path, 
                           validation_status='Not Validated', match_status='Waiting', validated_at=None, 
                           email='', payment_amount=None, payment_method=''):
        """Update Excel backup file"""
        try:
            wb = openpyxl.load_workbook(EXCEL_FILE)
            ws = wb.active
            
            row_data = [team_id, player1_name, player2_name, email, payment_status, 
                       payment_amount or '', payment_method, qr_path, 
                       validation_status, match_status, datetime.now().isoformat(), 
                       validated_at.isoformat() if validated_at else '']
            ws.append(row_data)
            wb.save(EXCEL_FILE)
        except Exception as e:
            print(f"Excel update error: {e}", flush=True)

    def export_teams_to_excel():
        """Export teams data from database to Excel file"""
        try:
            # Get all teams from database
            teams = execute_query('SELECT * FROM teams ORDER BY created_at DESC', fetch_all=True) or []
            
            wb = Workbook()
            ws = wb.active
            ws.title = "Teams Export"
            
            # Headers
            headers = ['Team ID', 'Player 1 Name', 'Player 2 Name', 'Email', 'Payment Status', 
                      'Payment Amount', 'Payment Method', 'QR Code Path', 'Validation Status', 
                      'Match Status', 'Created At', 'Validated At']
            ws.append(headers)
            
            # Add team data from database
            for team in teams:
                row_data = [
                    team.get('team_id', ''),
                    team.get('player1_name', ''),
                    team.get('player2_name', ''),
                    team.get('email', ''),
                    team.get('payment_status', 'Pending'),
                    team.get('payment_amount', ''),
                    team.get('payment_method', ''),
                    team.get('qr_code_path', ''),
                    team.get('validation_status', 'Not Validated'),
                    team.get('match_status', 'Waiting'),
                    team.get('created_at', '') if isinstance(team.get('created_at'), str) else team.get('created_at', '').isoformat() if team.get('created_at') else '',
                    team.get('validated_at', '') if isinstance(team.get('validated_at'), str) else team.get('validated_at', '').isoformat() if team.get('validated_at') else ''
                ]
                ws.append(row_data)
            
            # Save with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            export_filename = f'teams_export_{timestamp}.xlsx'
            wb.save(export_filename)
            
            print(f"✅ Exported {len(teams)} teams from database to {export_filename}")
            return export_filename
            
        except Exception as e:
            print(f"❌ Excel export error: {e}")
            return None

    def send_qr_email(email, team_id, player1_name, player2_name, qr_path):
        """Send QR code via email using SMTP directly"""
        try:
            print(f"Sending QR code email to {email}...", flush=True)
            
            # Create multipart message
            msg = MIMEMultipart('related')
            msg['Subject'] = f'Team Registration QR Code - Team {team_id}'
            msg['From'] = app.config['MAIL_USERNAME']
            msg['To'] = email
            
            # Create HTML content
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #007bff; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                    .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                    .qr-container {{ text-align: center; margin: 20px 0; }}
                    .qr-code {{ max-width: 200px; border: 2px solid #dee2e6; border-radius: 8px; padding: 10px; background: white; }}
                    .team-info {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                    .instructions {{ background: #d4edda; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #6c757d; font-size: 14px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎯 Team Registration Successful!</h1>
                    </div>
                    <div class="content">
                        <div class="team-info">
                            <h2>Team Details</h2>
                            <p><strong>Team ID:</strong> {team_id}</p>
                            <p><strong>Player 1:</strong> {player1_name}</p>
                            <p><strong>Player 2:</strong> {player2_name}</p>
                        </div>
                        
                        <div class="qr-container">
                            <h3>Your Team QR Code</h3>
                            <img src="cid:qr_code" alt="Team QR Code" class="qr-code">
                        </div>
                        
                        <div class="instructions">
                            <h4>📋 Important Instructions:</h4>
                            <ul>
                                <li>✅ Save this QR code on your phone</li>
                                <li>✅ Present it at the venue for validation</li>
                                <li>✅ Keep your Team ID: <strong>{team_id}</strong></li>
                                <li>✅ Both players must be present during validation</li>
                            </ul>
                        </div>
                        
                        <p>Good luck with your match! 🏆</p>
                    </div>
                    <div class="footer">
                        <p>Team Registration System | Powered by QR Technology</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Plain text version
            text_body = f"""
Team Registration Successful!

Team Details:
- Team ID: {team_id}
- Player 1: {player1_name}
- Player 2: {player2_name}

Your QR code is attached to this email.

Important Instructions:
- Save this QR code on your phone
- Present it at the venue for validation
- Keep your Team ID: {team_id}
- Both players must be present during validation

Good luck with your match!

Team Registration System
            """
            
            # Create alternative container
            msg_alternative = MIMEMultipart('alternative')
            msg.attach(msg_alternative)
            
            # Add text and HTML parts
            text_part = MIMEText(text_body, 'plain')
            html_part = MIMEText(html_body, 'html')
            msg_alternative.attach(text_part)
            msg_alternative.attach(html_part)
            
            # Attach QR code image
            with open(qr_path, 'rb') as f:
                qr_image_data = f.read()
                qr_image = MIMEImage(qr_image_data)
                qr_image.add_header('Content-ID', '<qr_code>')
                qr_image.add_header('Content-Disposition', 'inline', filename=f'team_{team_id}_qr.png')
                msg.attach(qr_image)
            
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

    # Routes
    @app.route('/')
    def index():
        """Home page with navigation"""
        return render_template('index.html')

    @app.route('/register')
    def register_page():
        """Team registration page"""
        return render_template('register.html')

    @app.route('/register', methods=['POST'])
    def register_team():
        """Handle team registration"""
        try:
            player1_name = request.form.get('player1_name')
            player2_name = request.form.get('player2_name')
            email = request.form.get('email', '').strip()
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
            
            # Generate QR code
            qr_data = generate_qr_data(team_id)
            qr_path = generate_qr_code(team_id, qr_data)
            
            # Store in database
            execute_query('''
                INSERT INTO teams (team_id, player1_name, player2_name, email, payment_status, 
                                 payment_amount, payment_method, qr_code_path)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (team_id, player1_name, player2_name, email or None, payment_status, 
                  payment_amount_float, payment_method or None, qr_path))
            
            # Update Excel backup
            update_excel_backup(team_id, player1_name, player2_name, payment_status, qr_path, 
                              email=email, payment_amount=payment_amount_float, payment_method=payment_method)
            
            # Send email with QR code if email provided
            email_sent = False
            if email and app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']:
                try:
                    send_qr_email(email, team_id, player1_name, player2_name, qr_path)
                    email_sent = True
                    flash('QR code sent to your email!', 'success')
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
                                 player2_name=player2_name,
                                 email=email,
                                 email_sent=email_sent,
                                 payment_amount=payment_amount_float,
                                 payment_method=payment_method,
                                 payment_status=payment_status)
            
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'error')
            return redirect(url_for('register_page'))

    @app.route('/validate')
    def validate_page():
        """QR code validation page"""
        return render_template('validate.html')

    @app.route('/validate', methods=['POST'])
    def validate_qr():
        """Handle QR code validation"""
        try:
            qr_data = request.json.get('qr_data')
            
            if not qr_data:
                return jsonify({'success': False, 'message': 'No QR data provided'})
            
            # Decrypt QR data
            try:
                encrypted_data = base64.urlsafe_b64decode(qr_data.encode())
                decrypted_data = cipher_suite.decrypt(encrypted_data)
                data = json.loads(decrypted_data.decode())
                team_id = data.get('team_id')
            except Exception as e:
                return jsonify({'success': False, 'message': 'Invalid QR code'})
            
            # Check if team exists and validate
            team = execute_query('SELECT * FROM teams WHERE team_id = %s', (team_id,), fetch_one=True)
            
            if not team:
                return jsonify({'success': False, 'message': 'Team not found'})
            
            if team['validation_status'] == 'Validated':
                return jsonify({'success': False, 'message': 'Team already validated'})
            
            # Update validation status and set to Playing
            execute_query('''
                UPDATE teams 
                SET validation_status = 'Validated', 
                    validated_at = CURRENT_TIMESTAMP,
                    match_status = 'Playing'
                WHERE team_id = %s
            ''', (team_id,))
            
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
    def monitor_dashboard():
        """Live monitor dashboard"""
        return render_template('monitor.html')

    @app.route('/monitor/complete_team', methods=['POST'])
    def complete_team_from_monitor():
        """Mark team as completed from monitor dashboard"""
        try:
            print(f"🔄 Complete team request received")
            team_id = request.json.get('team_id')
            print(f"📝 Team ID: {team_id}")
            
            if not team_id:
                return jsonify({'success': False, 'message': 'Team ID is required'})
            
            # Get team details first
            print(f"🔍 Looking up team {team_id}")
            team = execute_query('SELECT * FROM teams WHERE team_id = %s', (team_id,), fetch_one=True)
            print(f"📊 Team found: {team is not None}")
            
            if not team:
                return jsonify({'success': False, 'message': 'Team not found'})
            
            print(f"📋 Current team status: {team['match_status']}")
            if team['match_status'] != 'Playing':
                return jsonify({'success': False, 'message': f'Team is not currently playing (status: {team["match_status"]})'})
            
            # Update team status to Completed
            print(f"🔄 Updating team {team_id} from {team['match_status']} to Completed")
            result = execute_query('UPDATE teams SET match_status = %s WHERE team_id = %s', 
                                  ('Completed', team_id))
            
            print(f"📊 Database update result: {result}")
            
            if result:
                # Emit real-time update to all connected clients
                socketio.emit('team_completed', {
                    'team_id': team_id,
                    'player1_name': team['player1_name'],
                    'player2_name': team['player2_name'],
                    'status': 'Completed',
                    'completed_by': 'Monitor',
                    'timestamp': datetime.now().isoformat()
                })
                
                # Send special notification to admin
                socketio.emit('admin_notification', {
                    'type': 'team_completed',
                    'title': 'Match Completed',
                    'message': f"Team {team_id} ({team['player1_name']} & {team['player2_name']}) has completed their match!",
                    'team_id': team_id,
                    'timestamp': datetime.now().isoformat(),
                    'priority': 'high'
                })
                
                print(f"✅ Team {team_id} marked as completed from monitor")
                
                return jsonify({
                    'success': True, 
                    'message': 'Team marked as completed successfully',
                    'team': {
                        'team_id': team_id,
                        'player1_name': team['player1_name'],
                        'player2_name': team['player2_name'],
                        'status': 'Completed'
                    }
                })
            
            return jsonify({'success': False, 'message': 'Database update failed'})
            
        except Exception as e:
            print(f"Complete team error: {e}")
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/test/create_playing_team', methods=['POST'])
    def create_test_playing_team():
        """Create a test team in Playing status for testing completion"""
        try:
            team_id = str(uuid.uuid4())[:8].upper()
            
            # Generate QR code
            qr_data = generate_qr_data(team_id)
            qr_path = generate_qr_code(team_id, qr_data)
            
            # Store in database with Playing status
            result = execute_query('''
                INSERT INTO teams (team_id, player1_name, player2_name, email, payment_status, 
                                 payment_amount, payment_method, qr_code_path, validation_status, match_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (team_id, 'Test Player 1', 'Test Player 2', 'test@example.com', 'Paid', 
                  100.0, 'UPI', qr_path, 'Validated', 'Playing'))
            
            if result:
                print(f"✅ Created test playing team: {team_id}")
                return jsonify({
                    'success': True, 
                    'message': f'Test playing team created: {team_id}',
                    'team_id': team_id
                })
            
            return jsonify({'success': False, 'message': 'Failed to create test team'})
            
        except Exception as e:
            print(f"Create test team error: {e}")
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/admin')
    def admin_panel():
        """Admin panel"""
        teams = execute_query('SELECT * FROM teams ORDER BY created_at DESC', fetch_all=True) or []
        return render_template('admin.html', teams=teams)

    @app.route('/admin/update_status', methods=['POST'])
    def update_team_status():
        """Update team match status"""
        try:
            team_id = request.json.get('team_id')
            new_status = request.json.get('status')
            
            result = execute_query('UPDATE teams SET match_status = %s WHERE team_id = %s', 
                                  (new_status, team_id))
            
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
            
            # Get team details first
            team = execute_query('SELECT * FROM teams WHERE team_id = %s', (team_id,), fetch_one=True)
            
            if not team:
                return jsonify({'success': False, 'message': 'Team not found'})
            
            # Delete QR code file if it exists
            qr_path = team.get('qr_code_path')
            if qr_path and os.path.exists(qr_path):
                try:
                    os.remove(qr_path)
                    print(f"✅ Deleted QR code file: {qr_path}", flush=True)
                except Exception as e:
                    print(f"Warning: Could not delete QR file {qr_path}: {e}", flush=True)
            
            # Delete from database
            result = execute_query('DELETE FROM teams WHERE team_id = %s', (team_id,))
            
            if result:
                # Emit real-time update
                socketio.emit('team_deleted', {
                    'team_id': team_id,
                    'player1_name': team['player1_name'],
                    'player2_name': team['player2_name']
                })
                
                return jsonify({'success': True, 'message': 'Team deleted successfully'})
            
            return jsonify({'success': False, 'message': 'Database error'})
            
        except Exception as e:
            print(f"Delete team error: {e}", flush=True)
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/admin/delete_all_teams', methods=['POST'])
    def delete_all_teams():
        """Delete all teams"""
        try:
            # Get all teams first to clean up QR files
            teams = execute_query('SELECT * FROM teams', fetch_all=True) or []
            
            # Delete all QR code files
            qr_dir = 'static/qr_codes'
            if os.path.exists(qr_dir):
                qr_files = [f for f in os.listdir(qr_dir) if f.endswith('.png')]
                for qr_file in qr_files:
                    try:
                        os.remove(os.path.join(qr_dir, qr_file))
                    except Exception as e:
                        print(f"Warning: Could not delete QR file {qr_file}: {e}", flush=True)
                print(f"✅ Deleted {len(qr_files)} QR code files", flush=True)
            
            # Delete all teams from database
            result = execute_query('DELETE FROM teams')
            
            if result:
                # Emit real-time update
                socketio.emit('all_teams_deleted', {
                    'count': len(teams),
                    'message': 'All teams have been deleted'
                })
                
                return jsonify({'success': True, 'message': f'Successfully deleted {len(teams)} teams'})
            
            return jsonify({'success': False, 'message': 'Database error'})
            
        except Exception as e:
            print(f"Delete all teams error: {e}", flush=True)
            return jsonify({'success': False, 'message': str(e)})

    @app.route('/api/teams')
    def get_teams():
        """API endpoint to get all teams from database"""
        teams = execute_query('SELECT * FROM teams ORDER BY created_at DESC', fetch_all=True) or []
        
        # Convert datetime objects to strings for JSON serialization
        for team in teams:
            if team.get('created_at'):
                if not isinstance(team['created_at'], str):
                    team['created_at'] = team['created_at'].isoformat()
            if team.get('validated_at'):
                if not isinstance(team['validated_at'], str):
                    team['validated_at'] = team['validated_at'].isoformat()
        
        return jsonify(teams)

    @app.route('/api/stats')
    def get_stats():
        """API endpoint to get team statistics from database"""
        stats = {'total': 0, 'validated': 0, 'playing': 0, 'completed': 0}
        
        try:
            conn = get_db_connection()
            if conn:
                cur = get_cursor(conn)
                
                # Get statistics from database
                queries = [
                    ('SELECT COUNT(*) FROM teams', 'total'),
                    ("SELECT COUNT(*) FROM teams WHERE validation_status = 'Validated'", 'validated'),
                    ("SELECT COUNT(*) FROM teams WHERE match_status = 'Playing'", 'playing'),
                    ("SELECT COUNT(*) FROM teams WHERE match_status = 'Completed'", 'completed')
                ]
                
                for query, key in queries:
                    cur.execute(query)
                    result = cur.fetchone()
                    stats[key] = result[0] if result else 0
                
                cur.close()
                conn.close()
        except Exception as e:
            print(f"Stats query error: {e}")
        
        return jsonify(stats)

    @app.route('/admin/export', methods=['GET'])
    def export_data():
        """Export teams data to Excel"""
        try:
            filename = export_teams_to_excel()
            if filename:
                from flask import send_file
                return send_file(filename, as_attachment=True, download_name=filename)
            else:
                return jsonify({'success': False, 'message': 'Export failed'}), 500
        except Exception as e:
            print(f"Export error: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/admin/export_stats', methods=['GET'])
    def export_stats():
        """Export detailed statistics to Excel"""
        try:
            wb = Workbook()
            
            # Teams sheet
            ws_teams = wb.active
            ws_teams.title = "Teams"
            teams = execute_query('SELECT * FROM teams ORDER BY created_at DESC', fetch_all=True) or []
            
            headers = ['Team ID', 'Player 1 Name', 'Player 2 Name', 'Email', 'Payment Status', 
                      'Payment Amount', 'Payment Method', 'QR Code Path', 'Validation Status', 
                      'Match Status', 'Created At', 'Validated At']
            ws_teams.append(headers)
            
            for team in teams:
                row_data = [
                    team.get('team_id', ''),
                    team.get('player1_name', ''),
                    team.get('player2_name', ''),
                    team.get('email', ''),
                    team.get('payment_status', 'Pending'),
                    team.get('payment_amount', ''),
                    team.get('payment_method', ''),
                    team.get('qr_code_path', ''),
                    team.get('validation_status', 'Not Validated'),
                    team.get('match_status', 'Waiting'),
                    team.get('created_at', '') if isinstance(team.get('created_at'), str) else team.get('created_at', '').isoformat() if team.get('created_at') else '',
                    team.get('validated_at', '') if isinstance(team.get('validated_at'), str) else team.get('validated_at', '').isoformat() if team.get('validated_at') else ''
                ]
                ws_teams.append(row_data)
            
            # Statistics sheet
            ws_stats = wb.create_sheet("Statistics")
            stats_headers = ['Metric', 'Count', 'Percentage']
            ws_stats.append(stats_headers)
            
            total_teams = len(teams)
            validated_teams = len([t for t in teams if t.get('validation_status') == 'Validated'])
            playing_teams = len([t for t in teams if t.get('match_status') == 'Playing'])
            completed_teams = len([t for t in teams if t.get('match_status') == 'Completed'])
            paid_teams = len([t for t in teams if t.get('payment_status') == 'Paid'])
            
            stats_data = [
                ['Total Teams', total_teams, '100%'],
                ['Validated Teams', validated_teams, f'{(validated_teams/total_teams*100):.1f}%' if total_teams > 0 else '0%'],
                ['Currently Playing', playing_teams, f'{(playing_teams/total_teams*100):.1f}%' if total_teams > 0 else '0%'],
                ['Completed Matches', completed_teams, f'{(completed_teams/total_teams*100):.1f}%' if total_teams > 0 else '0%'],
                ['Paid Teams', paid_teams, f'{(paid_teams/total_teams*100):.1f}%' if total_teams > 0 else '0%']
            ]
            
            for row in stats_data:
                ws_stats.append(row)
            
            # Save with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            export_filename = f'teams_detailed_export_{timestamp}.xlsx'
            wb.save(export_filename)
            
            print(f"✅ Exported detailed report with {total_teams} teams to {export_filename}")
            
            from flask import send_file
            return send_file(export_filename, as_attachment=True, download_name=export_filename)
            
        except Exception as e:
            print(f"Detailed export error: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @socketio.on('connect')
    def handle_connect():
        print('Client connected', flush=True)

    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected', flush=True)

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
                print("✅ Excel backup file initialized")
            else:
                print("✅ Excel backup file already exists")
        except Exception as e:
            print(f"❌ Excel initialization error: {e}")

    # Initialize database and Excel for production
    print("=== Initializing Application ===")
    init_database()
    init_excel()
    
    # Test database connection
    test_conn = get_db_connection()
    if test_conn:
        print("✅ Database connection test successful")
        test_conn.close()
    else:
        print("❌ Database connection test failed")
    
    print("✅ Application initialized successfully")

    if __name__ == '__main__':
        print("=== Starting Development Server ===")
        port = int(PORT)
        print(f"� BStarting server on port {port}")
        print(f"🌐 Access the application at: http://localhost:{port}")
        print(f"📊 Basic Export: http://localhost:{port}/admin/export")
        print(f"📈 Detailed Export: http://localhost:{port}/admin/export_stats")
        
        socketio.run(app, debug=True, host='0.0.0.0', port=port)

except Exception as e:
    print(f"❌ Application startup failed: {e}", flush=True)
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")