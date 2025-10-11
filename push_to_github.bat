@echo off
echo 🚀 MatchPulse GitHub Push Script
echo ================================

echo Step 1: Updating remote repository URL...
git remote set-url origin https://github.com/taksh1507/MatchPulse1.git

echo Step 2: Verifying remote URL...
git remote -v

echo Step 3: Adding all files...
git add .

echo Step 4: Committing files...
git commit -m "🚀 Complete MatchPulse System - Production Ready

✨ Features:
- Real-time tournament monitoring with Socket.IO
- Mobile-responsive design with Bootstrap 5
- QR code generation and validation system
- Indian mobile number validation with +91 prefix
- Random password generation for security
- Public queue page for participants
- Goal time tracking and leaderboard
- Email notifications with queue information
- Database migration system
- Excel export with detailed statistics

🔧 Technical Stack:
- Flask with PostgreSQL/SQLite support
- Socket.IO for real-time updates
- Bootstrap 5 responsive UI framework
- Encrypted QR codes for security
- SMTP email integration
- Heroku deployment configuration

📱 Mobile Optimized:
- Touch-friendly interface
- Responsive design
- Mobile-first approach
- Fast loading with caching"

echo Step 5: Setting main branch...
git branch -M main

echo Step 6: Pushing to GitHub...
git push -u origin main

echo ✅ Push completed! Check https://github.com/taksh1507/MatchPulse1.git
pause