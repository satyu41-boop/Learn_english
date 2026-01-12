"""
Notification services for sending transcripts.
Supports Email (Gmail SMTP), SMS (carrier gateways), and WhatsApp (Twilio).
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config


class NotificationError(Exception):
    """Custom exception for notification failures."""
    pass


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Send email via Gmail SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body (plain text)
    
    Returns:
        True if sent successfully
    
    Raises:
        NotificationError: If sending fails
    """
    if not config.SMTP_EMAIL or not config.SMTP_PASSWORD:
        raise NotificationError(
            "Email not configured. Please set SMTP_EMAIL and SMTP_PASSWORD in your .env file."
        )
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = config.SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect and send
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_EMAIL, config.SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
    
    except smtplib.SMTPAuthenticationError:
        raise NotificationError(
            "Gmail authentication failed. Make sure you're using an App Password, "
            "not your regular Gmail password."
        )
    except Exception as e:
        raise NotificationError(f"Failed to send email: {str(e)}")


def send_sms(phone_number: str, carrier: str, message: str) -> bool:
    """
    Send SMS via email-to-SMS gateway.
    
    Args:
        phone_number: 10-digit phone number (no country code)
        carrier: Carrier name (e.g., 'airtel', 'jio')
        message: SMS message (max 160 chars recommended)
    
    Returns:
        True if sent successfully
    
    Raises:
        NotificationError: If sending fails
    """
    if carrier not in config.SMS_GATEWAYS:
        raise NotificationError(
            f"Unsupported carrier: {carrier}. "
            f"Supported carriers: {', '.join(config.SMS_GATEWAYS.keys())}"
        )
    
    # Clean phone number (remove spaces, dashes, country code)
    phone = ''.join(filter(str.isdigit, phone_number))
    if len(phone) > 10:
        phone = phone[-10:]  # Take last 10 digits
    
    # Create SMS gateway email
    gateway_email = f"{phone}{config.SMS_GATEWAYS[carrier]}"
    
    # SMS should be short
    if len(message) > 1600:
        message = message[:1597] + "..."
    
    try:
        return send_email(gateway_email, "", message)
    except NotificationError:
        raise
    except Exception as e:
        raise NotificationError(f"Failed to send SMS: {str(e)}")


def send_whatsapp(to_number: str, message: str) -> bool:
    """
    Send WhatsApp message via Twilio Sandbox.
    
    Args:
        to_number: WhatsApp number with country code (e.g., +919876543210)
        message: Message to send
    
    Returns:
        True if sent successfully
    
    Raises:
        NotificationError: If sending fails
    """
    if not config.TWILIO_ACCOUNT_SID or not config.TWILIO_AUTH_TOKEN:
        raise NotificationError(
            "WhatsApp not configured. Please set TWILIO_ACCOUNT_SID and "
            "TWILIO_AUTH_TOKEN in your .env file."
        )
    
    try:
        from twilio.rest import Client
        
        client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
        
        # Ensure number has whatsapp: prefix
        if not to_number.startswith('whatsapp:'):
            to_number = f"whatsapp:{to_number}"
        
        message = client.messages.create(
            body=message,
            from_=config.TWILIO_WHATSAPP_FROM,
            to=to_number
        )
        
        return message.sid is not None
    
    except ImportError:
        raise NotificationError(
            "Twilio library not installed. Run: pip install twilio"
        )
    except Exception as e:
        error_msg = str(e)
        if 'not a valid WhatsApp' in error_msg:
            raise NotificationError(
                "This number hasn't joined the Twilio WhatsApp Sandbox. "
                "Ask the user to send 'join <sandbox-code>' to the Twilio number first."
            )
        raise NotificationError(f"Failed to send WhatsApp: {error_msg}")


def format_transcript_message(transcript: str, url: str, language: str) -> str:
    """
    Format transcript for notification.
    
    Args:
        transcript: The transcript text
        url: Instagram video URL
        language: Detected language
    
    Returns:
        Formatted message
    """
    return f"""🎬 Instagram Video Transcript

📺 Video: {url}
🌍 Language: {language}

📝 Transcript:
{'-' * 30}
{transcript}
{'-' * 30}

Generated by Instagram Transcriber
"""


def format_transcript_email(transcript: str, url: str, language: str, line_count: int) -> tuple:
    """
    Format transcript for email with subject and body.
    
    Returns:
        Tuple of (subject, body)
    """
    subject = f"🎬 Your Instagram Transcript ({line_count} lines)"
    body = format_transcript_message(transcript, url, language)
    return subject, body
