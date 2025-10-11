#!/usr/bin/env python3
"""
WSGI Entry Point for Production Deployment
"""
import os

# Import the app and socketio from main module
from app_minimal_working import app, socketio

# Get port from environment (Render will set this automatically)
port = os.environ.get('PORT')
if port:
    print(f"🚀 WSGI: Port configured as {port}")
else:
    print("🚀 WSGI: Using default port configuration")

# For gunicorn, we need to expose the socketio app
application = socketio

# Ensure the app is ready for production
print("✅ WSGI: Application ready for gunicorn")