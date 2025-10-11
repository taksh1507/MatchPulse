# QR Code-Based Team Registration System

A comprehensive team registration and monitoring system with QR code validation, real-time updates, and mobile-friendly interface.

## 🚀 Features

- **Team Registration**: Web-based registration with instant QR code generation
- **Mobile QR Validation**: Mobile-friendly QR code scanning using device camera
- **Real-time Monitoring**: Live dashboard showing team status and match progress
- **Admin Panel**: Complete team management with status updates
- **Database Integration**: PostgreSQL with Excel backup
- **Real-time Updates**: WebSocket-based live updates across all dashboards
- **Mobile Responsive**: Optimized for mobile devices and tablets
- **Secure**: Encrypted QR codes with validation tokens

## 🛠️ Tech Stack

- **Backend**: Python Flask 3.0+, Flask-SocketIO
- **Database**: PostgreSQL (with Excel backup using openpyxl)
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **QR Code**: Python qrcode library + html5-qrcode for scanning
- **Real-time**: WebSocket (Socket.IO)
- **Deployment**: Render (with HTTPS)

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL database (local or cloud like Neon)
- Modern web browser with camera support for QR scanning

## 🔧 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd team-registration-system
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
```bash
cp .env.example .env
```

Edit `.env` file with your configuration:
```env
DATABASE_URL=postgresql://username:password@localhost/team_registration
SECRET_KEY=your-super-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here
PORT=5000
```

### 5. Database Setup

#### Option A: Local PostgreSQL
```bash
# Create database
createdb team_registration

# Update DATABASE_URL in .env
DATABASE_URL=postgresql://localhost/team_registration
```

#### Option B: Neon (Cloud PostgreSQL)
1. Sign up at [Neon](https://neon.tech)
2. Create a new database
3. Copy connection string to `.env`

### 6. Run the Application
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## 🌐 Deployment on Render

### 1. Prepare for Deployment
- Ensure all files are committed to Git
- Push to GitHub repository

### 2. Create Render Web Service
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: team-registration-system
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --worker-class eventlet -w 1 app:app`

### 3. Environment Variables
Add these environment variables in Render:
```
DATABASE_URL=your-postgresql-connection-string
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-encryption-key
```

### 4. Database Setup
- Use Render PostgreSQL or external service like Neon
- Database tables will be created automatically on first run

## 📱 Usage Guide

### For Event Organizers

#### 1. Team Registration
- Navigate to `/register`
- Enter player names and payment status
- System generates unique Team ID and QR code
- QR code can be downloaded or printed

#### 2. Admin Panel (`/admin`)
- View all registered teams
- Update team status (Waiting → Playing → Completed)
- Download QR codes
- View team statistics

#### 3. Live Monitor (`/monitor`)
- Real-time dashboard for event display
- Shows currently playing teams
- Lists validated teams ready to play
- Auto-updates when teams are validated

### For Volunteers/Staff

#### QR Code Validation (`/validate`)
- Mobile-friendly QR scanner
- Point camera at team's QR code
- Instant validation with team details
- Prevents duplicate validations
- Audio/visual feedback on successful scan

### For Participants

#### Registration Process
1. Register team online or on-site
2. Receive QR code (download/email/print)
3. Present QR code at venue for validation
4. Monitor status on live dashboard

## 🔒 Security Features

- **Encrypted QR Codes**: QR data is encrypted with timestamp validation
- **Duplicate Prevention**: Teams cannot be validated multiple times
- **Secure Database**: PostgreSQL with parameterized queries
- **HTTPS**: Secure connections in production

## 📊 API Endpoints

- `GET /api/teams` - Get all teams data
- `GET /api/stats` - Get team statistics
- `POST /validate` - Validate QR code
- `POST /admin/update_status` - Update team status

## 🔄 Real-time Events

The system uses WebSocket for real-time updates:
- `team_registered` - New team registration
- `team_validated` - Team QR code validated
- `status_updated` - Team status changed
- `stats_update` - Statistics updated

## 📁 Project Structure

```
team-registration-system/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Procfile              # Render deployment config
├── runtime.txt           # Python version
├── .env.example          # Environment variables template
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── register.html
│   ├── registration_success.html
│   ├── validate.html
│   ├── monitor.html
│   └── admin.html
├── static/               # Static files
│   ├── css/
│   │   └── custom.css
│   └── qr_codes/        # Generated QR codes
└── teams_backup.xlsx     # Excel backup file
```

## 🐛 Troubleshooting

### Common Issues

#### Database Connection Error
```bash
# Check PostgreSQL is running
pg_isready

# Verify connection string
psql $DATABASE_URL
```

#### QR Scanner Not Working
- Ensure HTTPS in production (required for camera access)
- Check browser permissions for camera
- Verify good lighting conditions

#### Real-time Updates Not Working
- Check WebSocket connection in browser console
- Verify no firewall blocking WebSocket connections
- Ensure eventlet is installed for production

### Development Tips

#### Reset Database
```python
# In Python shell
from app import init_database
init_database()
```

#### Generate New Encryption Key
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the API documentation

## 🎯 Roadmap

- [ ] Email notifications for QR codes
- [ ] Leaderboard and scoring system
- [ ] PWA support for offline scanning
- [ ] Push notifications
- [ ] Advanced reporting and analytics
- [ ] Multi-event support
- [ ] Team photo upload
- [ ] SMS notifications

---

**Built with ❤️ for seamless event management**