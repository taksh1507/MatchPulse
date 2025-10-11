# MatchPulse - Team Registration System

A comprehensive team registration and tournament management system built with Flask, featuring real-time monitoring, QR code validation, and mobile-responsive design.

## 🚀 Features

### 📋 Team Registration
- **Mobile-optimized registration form** with validation
- **Indian mobile number validation** with predefined +91 country code
- **QR code generation** for each team with encrypted data
- **Email notifications** with QR codes and queue information
- **Payment tracking** with multiple payment methods
- **Queue management** with group organization

### 🔐 Security & Authentication
- **Page-specific password protection** with random generation
- **Encrypted QR codes** for secure validation
- **Session management** with automatic expiration
- **Email-based password delivery** (sent only on first startup)

### 📱 Real-time Monitoring
- **Live team status updates** via WebSocket
- **Currently playing teams** with match controls
- **Queue visualization** with next teams display
- **Leaderboard** with goal time tracking
- **Mobile-responsive design** for all devices

### 🎯 Tournament Management
- **Team validation** via QR code scanning
- **Match status tracking** (Waiting → Playing → Completed)
- **Goal time recording** with leaderboard rankings
- **Winner identification** with phone number contact
- **Excel export** with detailed statistics

### 🌐 Public Features
- **Public queue page** for teams to check their position
- **Real-time updates** without admin access
- **Mobile-friendly interface** for participants
- **Tournament progress tracking**

## 🛠️ Technology Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL (production) / SQLite (development)
- **Real-time**: Socket.IO for live updates
- **Frontend**: Bootstrap 5, JavaScript
- **QR Codes**: Python qrcode library
- **Email**: SMTP with HTML templates
- **Deployment**: Heroku-ready with Procfile

## 📦 Installation

### Prerequisites
- Python 3.9+
- PostgreSQL (for production)
- SMTP email account

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/taksh1507/MatchPulse.git
   cd MatchPulse
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file:
   ```env
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=sqlite:///teams.db
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   ```

5. **Run the application**
   ```bash
   python app_ngrok_optimized.py
   ```

### Heroku Deployment

1. **Create Heroku app**
   ```bash
   heroku create your-app-name
   ```

2. **Add PostgreSQL addon**
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

3. **Set environment variables**
   ```bash
   heroku config:set SECRET_KEY=your-secret-key
   heroku config:set SMTP_SERVER=smtp.gmail.com
   heroku config:set SMTP_PORT=587
   heroku config:set SMTP_USERNAME=your-email@gmail.com
   heroku config:set SMTP_PASSWORD=your-app-password
   ```

4. **Deploy**
   ```bash
   git push heroku main
   ```

## 🔧 Configuration

### Email Setup
The system requires SMTP configuration for:
- QR code delivery to teams
- Password notifications to admin
- Winner notifications

### Database Migration
The app automatically handles database schema updates on startup.

### Password Management
- Passwords are randomly generated on first startup
- Stored in `page_passwords.json` (excluded from git)
- Can be regenerated via admin panel
- Sent via email to configured admin address

## 📱 Usage

### For Participants
1. **Register**: Fill out team registration form
2. **Receive QR Code**: Check email for QR code and queue number
3. **Check Queue**: Visit `/queue` to see current position
4. **Validate**: Present QR code at venue for validation
5. **Play**: Wait for your turn based on queue number

### For Organizers
1. **Monitor**: Use `/monitor` for real-time tournament tracking
2. **Validate**: Use `/validate` to scan QR codes and start matches
3. **Admin**: Use `/admin` for team management and exports
4. **Queue**: Public `/queue` page for participant reference

## 🎮 Tournament Flow

1. **Registration** → Teams register and receive QR codes
2. **Queue Assignment** → Teams get queue numbers and group assignments
3. **Validation** → QR codes scanned to mark teams as ready
4. **Playing** → Teams called in queue order to play matches
5. **Goal Recording** → Goal times recorded for leaderboard
6. **Completion** → Matches marked complete, winners identified

## 📊 Features Overview

### Pages & Access Levels
- **Home** (`/`) - Public access
- **Register** (`/register`) - Password protected
- **Queue** (`/queue`) - Public access
- **Validate** (`/validate`) - Password protected
- **Monitor** (`/monitor`) - Password protected
- **Admin** (`/admin`) - Password protected

### API Endpoints
- `/api/teams` - Team data
- `/api/queue` - Queue information
- `/api/leaderboard` - Goal time rankings
- `/api/stats` - Tournament statistics
- `/api/playing_queue` - Current playing order

### Real-time Events
- Team registration notifications
- Validation status updates
- Match completion alerts
- Goal time recordings
- Queue position changes

## 🔒 Security Features

- **Encrypted QR codes** with timestamp validation
- **Random password generation** for admin access
- **Session-based authentication** with expiration
- **Input validation** for all forms
- **Mobile number formatting** and validation
- **SQL injection prevention** with parameterized queries

## 📱 Mobile Optimization

- **Responsive design** for all screen sizes
- **Touch-friendly buttons** (minimum 44px)
- **Optimized forms** for mobile input
- **Fast loading** with efficient asset delivery
- **Offline-capable** QR code storage

## 🚀 Performance Features

- **Database caching** for frequently accessed data
- **Optimized queries** with proper indexing
- **Real-time updates** via WebSocket
- **Lazy loading** for large datasets
- **Compressed assets** for faster loading

## 📈 Analytics & Reporting

- **Excel export** with detailed team information
- **Leaderboard tracking** with goal times
- **Tournament statistics** and progress metrics
- **Winner identification** with contact information
- **Historical data** preservation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Taksh Gandhi**
- GitHub: [@taksh1507](https://github.com/taksh1507)
- Email: takshgandhi4@gmail.com

## 🙏 Acknowledgments

- Bootstrap for responsive UI components
- Flask community for excellent documentation
- Socket.IO for real-time functionality
- QR code libraries for secure validation

---

**MatchPulse** - Streamlining tournament management with modern web technology! 🏆