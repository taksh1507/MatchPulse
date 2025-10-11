#!/usr/bin/env python3
"""
Production runner for Team Registration System
Handles environment setup and graceful startup
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import after loading environment
from app_minimal_working import app, socketio

def main():
    """Main application runner"""
    print("🚀 Starting Team Registration System...")
    
    # Database and Excel are initialized within the app
    print("📊 Database and Excel will be initialized by the app...")
    
    # Get configuration
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"🌐 Server starting on {host}:{port}")
    print(f"🔧 Debug mode: {debug}")
    
    if not debug:
        print("🔒 Running in production mode")
        print("📱 QR validation will require HTTPS for camera access")
    
    try:
        # Start the application
        socketio.run(
            app, 
            host=host, 
            port=port, 
            debug=debug,
            allow_unsafe_werkzeug=True
        )
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Application error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()