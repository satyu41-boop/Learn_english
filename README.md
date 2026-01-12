# 🎬 Instagram Video Transcriber

Free tool to extract and transcribe speech from Instagram videos, reels, and IGTV.

![Screenshot](https://via.placeholder.com/800x400?text=Instagram+Transcriber)

## ✨ Features

- 🎤 **Speech-to-Text** - Powered by OpenAI Whisper
- 📧 **Email Delivery** - Send transcripts directly to any email
- 💬 **WhatsApp Delivery** - Send via WhatsApp (Twilio)
- 🔐 **User Accounts** - Login/register system
- � **Analytics Ready** - Google Analytics integration
- 💰 **Ad Ready** - Google AdSense integration
- �️ **MySQL Database** - Production-ready database

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- MySQL
- FFmpeg

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd instagram-transcriber

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup MySQL database
sudo mysql -e "CREATE DATABASE instagram_transcriber;"
sudo mysql -e "CREATE USER 'transcriber'@'localhost' IDENTIFIED BY 'transcriber123';"
sudo mysql -e "GRANT ALL ON instagram_transcriber.* TO 'transcriber'@'localhost';"

# Configure environment
cp .env.example .env
# Edit .env with your Gmail credentials

# Run the app
python app.py
```

Open http://localhost:5000

## ⚙️ Configuration

Edit `.env` file:

```env
# Email (Required for email delivery)
SMTP_EMAIL=your.email@gmail.com
SMTP_PASSWORD=your-gmail-app-password

# Analytics (Optional)
GA_MEASUREMENT_ID=G-XXXXXXXXXX

# Ads (Optional)
ADSENSE_PUB_ID=ca-pub-XXXXXXXXXX
```

## 🌐 Deployment

### Railway (Recommended)

1. Create account at [railway.app](https://railway.app)
2. Connect your GitHub repository
3. Add MySQL add-on
4. Set environment variables
5. Deploy!

## � License

MIT License

---

Made with ❤️ using Whisper AI
