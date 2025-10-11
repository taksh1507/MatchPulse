#!/usr/bin/env python3
"""
Setup script for Team Registration System
Automates the initial setup process
"""

import os
import sys
import subprocess
import secrets
from cryptography.fernet import Fernet

def run_command(command, description):
    """Run a shell command with error handling"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return None

def create_env_file():
    """Create .env file with generated secrets"""
    print("🔄 Creating environment configuration...")
    
    # Generate secure keys
    secret_key = secrets.token_urlsafe(32)
    encryption_key = Fernet.generate_key().decode()
    
    env_content = f"""# Team Registration System Configuration
# Generated on setup

# Database Configuration
DATABASE_URL=postgresql://localhost/team_registration

# Security Keys (Generated)
SECRET_KEY={secret_key}
ENCRYPTION_KEY={encryption_key}

# Server Configuration
PORT=5000

# Email Configuration (Optional - Configure if needed)
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USERNAME=your-email@gmail.com
# SMTP_PASSWORD=your-app-password
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Environment file created with secure keys")

def setup_database():
    """Setup PostgreSQL database"""
    print("🔄 Setting up database...")
    
    # Check if PostgreSQL is installed
    pg_check = run_command("pg_config --version", "Checking PostgreSQL installation")
    if not pg_check:
        print("⚠️  PostgreSQL not found. Please install PostgreSQL first.")
        print("   - macOS: brew install postgresql")
        print("   - Ubuntu: sudo apt-get install postgresql postgresql-contrib")
        print("   - Windows: Download from https://www.postgresql.org/download/")
        return False
    
    # Create database
    db_created = run_command("createdb team_registration", "Creating database")
    if not db_created:
        print("⚠️  Database creation failed. It might already exist or you need to start PostgreSQL service.")
        print("   Try: brew services start postgresql (macOS) or sudo service postgresql start (Linux)")
    
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("🔄 Installing Python dependencies...")
    
    # Upgrade pip first
    run_command(f"{sys.executable} -m pip install --upgrade pip", "Upgrading pip")
    
    # Install requirements
    result = run_command(f"{sys.executable} -m pip install -r requirements.txt", "Installing dependencies")
    return result is not None

def create_directories():
    """Create necessary directories"""
    print("🔄 Creating project directories...")
    
    directories = [
        'static/qr_codes',
        'static/css',
        'templates'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    print("✅ Project directories created")

def main():
    """Main setup function"""
    print("🚀 Team Registration System Setup")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version.split()[0]} detected")
    
    # Create directories
    create_directories()
    
    # Create .env file
    if not os.path.exists('.env'):
        create_env_file()
    else:
        print("⚠️  .env file already exists, skipping creation")
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Setup database
    setup_database()
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Review and update .env file if needed")
    print("2. Start PostgreSQL service if not running")
    print("3. Run the application: python app.py")
    print("4. Open http://localhost:5000 in your browser")
    print("\n📚 For deployment instructions, see README.md")
    print("\n🆘 Need help? Check the troubleshooting section in README.md")

if __name__ == "__main__":
    main()