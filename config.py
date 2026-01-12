"""
Configuration settings for Instagram Transcriber.
Copy this file to config.py and fill in your credentials.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Flask settings
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database settings (MySQL)
DB_USER = os.getenv('DB_USER', 'transcriber')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'transcriber123')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'instagram_transcriber')

# Get DATABASE_URL or build it
uri = os.getenv('DATABASE_URL')
if uri and uri.startswith('mysql://'):
    uri = uri.replace('mysql://', 'mysql+pymysql://', 1)

SQLALCHEMY_DATABASE_URI = uri or f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Whisper settings
WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')

# Email settings (Gmail SMTP)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_EMAIL = os.getenv('SMTP_EMAIL', '')  # Your Gmail address
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')  # Gmail App Password

# Twilio settings (for WhatsApp - optional)
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_WHATSAPP_FROM = os.getenv('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')

# SMS Email-to-SMS Gateways (Indian carriers)
SMS_GATEWAYS = {
    'airtel': '@airtelmail.com',
    'jio': '@jio.com',
    'vi': '@vimail.com',
    'bsnl': '@bsnl.in',
    # US carriers (for reference)
    'att': '@txt.att.net',
    'tmobile': '@tmomail.net',
    'verizon': '@vtext.com',
}

# Google Analytics (optional)
GA_MEASUREMENT_ID = os.getenv('GA_MEASUREMENT_ID', '')  # e.g., G-XXXXXXXXXX

# Google AdSense (optional)
ADSENSE_PUB_ID = os.getenv('ADSENSE_PUB_ID', '')  # e.g., ca-pub-XXXXXXXXXX
