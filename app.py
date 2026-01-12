"""
Instagram Video Transcriber - Flask Backend
Extracts speech from Instagram videos and converts to text script.
With authentication and multi-channel delivery.
"""

import os
import uuid
import shutil
import subprocess
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

import config
from models import db, User, Transcript
import notifications

app = Flask(__name__)

# Load configuration
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'
login_manager.login_message = 'Please log in to transcribe videos.'

# Configuration
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), 'downloads')
WHISPER_MODEL = config.WHISPER_MODEL

# Ensure download directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Lazy load whisper model
_whisper_model = None


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def get_whisper_model():
    """Lazy load Whisper model to avoid slow startup."""
    global _whisper_model
    if _whisper_model is None:
        import whisper
        print(f"Loading Whisper '{WHISPER_MODEL}' model (first time may take a minute)...")
        _whisper_model = whisper.load_model(WHISPER_MODEL)
        print("Model loaded successfully!")
    return _whisper_model


from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'mp3', 'wav', 'mp4', 'm4a', 'mov', 'webm'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

import yt_dlp

def download_video(url: str, output_dir: str) -> str:
    """Download video from YouTube or other sources using yt-dlp library."""
    video_id = str(uuid.uuid4())[:8]
    # Configure yt-dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, f'{video_id}.%(ext)s'),
        'noplaylist': True,
        'max_filesize': 200 * 1024 * 1024, # 200MB
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print(f"YT-DLP ERROR: {str(e)}")
        raise Exception(f"Download failed. Error: {str(e)[:200]}...")
    
    for f in os.listdir(output_dir):
        if f.startswith(video_id):
            return os.path.join(output_dir, f)
    
    raise Exception("Video downloaded but file not found")


import shutil

def extract_audio(video_path: str) -> str:
    """Extract audio from video using ffmpeg."""
    # If already audio (mp3/wav), just return or convert if needed
    ext = video_path.rsplit('.', 1)[1].lower()
    if ext in ['wav', 'mp3', 'm4a']:
        pass

    audio_path = video_path.rsplit('.', 1)[0] + '.wav'
    
    # Robustly find ffmpeg
    ffmpeg_binary = shutil.which('ffmpeg')
    if not ffmpeg_binary:
        # Common fallback locations
        common_paths = ['/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg', '/opt/homebrew/bin/ffmpeg']
        for p in common_paths:
            if os.path.exists(p):
                ffmpeg_binary = p
                break
    
    if not ffmpeg_binary:
        raise Exception("FFmpeg binary not found in system PATH. Please install FFmpeg.")

    cmd = [
        ffmpeg_binary,
        '-i', video_path,
        '-vn',
        '-acodec', 'pcm_s16le',
        '-ar', '16000',
        '-ac', '1',
        '-y',
        audio_path
    ]
    
    # Debug logging
    print(f"Executing FFmpeg: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"FFMPEG ERROR: {result.stderr}")
        raise Exception(f"Failed to extract audio: {result.stderr}")
        
    return audio_path


def transcribe_audio(audio_path: str) -> dict:
    """Transcribe audio using Whisper."""
    model = get_whisper_model()
    result = model.transcribe(audio_path, language=None)
    return result


def format_transcript(result: dict) -> str:
    """Format transcription result as line-by-line script."""
    lines = []
    
    for segment in result.get('segments', []):
        text = segment.get('text', '').strip()
        if text:
            lines.append(text)
    
    if not lines and result.get('text'):
        text = result['text'].strip()
        for sep in ['. ', '? ', '! ']:
            text = text.replace(sep, sep + '\n')
        lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    return '\n'.join(lines)


# ==================== Routes ====================

@app.route('/')
def index():
    """Serve the main web interface."""
    return render_template('index.html', config=config)


@app.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()
    
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    
    if not email or not password:
        return jsonify({'success': False, 'error': 'Email and password are required'}), 400
    
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'error': 'Email already registered'}), 400
    
    user = User(email=email, name=name)
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    login_user(user)
    
    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name
        }
    })


@app.route('/login', methods=['POST'])
def login():
    """Log in an existing user."""
    data = request.get_json()
    
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'success': False, 'error': 'Email and password are required'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        return jsonify({'success': False, 'error': 'Invalid email or password'}), 401
    
    login_user(user)
    
    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'phone': user.phone,
            'phone_carrier': user.phone_carrier,
            'whatsapp': user.whatsapp
        }
    })


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    return jsonify({'success': True})


@app.route('/me')
def get_current_user():
    """Get current user info."""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'email': current_user.email,
                'name': current_user.name,
                'phone': current_user.phone,
                'phone_carrier': current_user.phone_carrier,
                'whatsapp': current_user.whatsapp
            }
        })
    return jsonify({'authenticated': False})


@app.route('/profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile (phone, WhatsApp, etc.)."""
    data = request.get_json()
    
    if 'name' in data:
        current_user.name = data['name'].strip()
    if 'phone' in data:
        current_user.phone = data['phone'].strip()
    if 'phone_carrier' in data:
        current_user.phone_carrier = data['phone_carrier'].strip()
    if 'whatsapp' in data:
        current_user.whatsapp = data['whatsapp'].strip()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'user': {
            'id': current_user.id,
            'email': current_user.email,
            'name': current_user.name,
            'phone': current_user.phone,
            'phone_carrier': current_user.phone_carrier,
            'whatsapp': current_user.whatsapp
        }
    })


@app.route('/transcribe', methods=['POST'])
@login_required
def transcribe():
    """Transcribe a video (from URL or File Upload)."""
    try:
        url = None
        video_path = None
        temp_dir = os.path.join(DOWNLOAD_DIR, str(uuid.uuid4()))
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Check if it's a file upload
            if 'file' in request.files:
                file = request.files['file']
                if file.filename == '':
                    return jsonify({'success': False, 'error': 'No file selected'}), 400
                
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    video_path = os.path.join(temp_dir, filename)
                    file.save(video_path)
                    url = f"File: {filename}"  # Placeholder for DB
                else:
                    return jsonify({'success': False, 'error': 'Invalid file type. Allowed: mp3, wav, mp4, m4a, mov'}), 400
            
            # Check if it's a URL
            else:
                # Handle JSON or Form data
                if request.is_json:
                    data = request.get_json()
                    url = data.get('url', '').strip()
                else:
                    url = request.form.get('url', '').strip()
                
                if not url:
                    return jsonify({'success': False, 'error': 'Please provide a Video URL or upload a file'}), 400
                
                video_path = download_video(url, temp_dir)

            # Process the video/audio
            audio_path = extract_audio(video_path)
            result = transcribe_audio(audio_path)
            transcript = format_transcript(result)
            
            if not transcript:
                return jsonify({
                    'success': False, 
                    'error': 'No speech detected in the video.'
                }), 400
            
            language = result.get('language', 'unknown')
            line_count = len(transcript.split('\n'))
            
            # Save transcript to database
            transcript_record = Transcript(
                user_id=current_user.id,
                instagram_url=url,  # We use this field for both URL and Filename
                transcript_text=transcript,
                language=language,
                line_count=line_count
            )
            db.session.add(transcript_record)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'transcript_id': transcript_record.id,
                'transcript': transcript,
                'language': language,
                'line_count': line_count,
                'url': url
            })
            
        finally:
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/transcript/<int:transcript_id>')
@login_required
def get_transcript(transcript_id):
    """Get a specific transcript."""
    transcript = Transcript.query.filter_by(id=transcript_id, user_id=current_user.id).first()
    
    if not transcript:
        return jsonify({'success': False, 'error': 'Transcript not found'}), 404
    
    return jsonify({
        'success': True,
        'transcript': {
            'id': transcript.id,
            'url': transcript.instagram_url,
            'text': transcript.transcript_text,
            'language': transcript.language,
            'line_count': transcript.line_count,
            'created_at': transcript.created_at.isoformat()
        }
    })


@app.route('/send/<int:transcript_id>', methods=['POST'])
@login_required
def send_transcript(transcript_id):
    """Send transcript via email, SMS, or WhatsApp."""
    transcript = Transcript.query.filter_by(id=transcript_id, user_id=current_user.id).first()
    
    if not transcript:
        return jsonify({'success': False, 'error': 'Transcript not found'}), 404
    
    data = request.get_json()
    method = data.get('method', 'email')
    
    try:
        if method == 'email':
            if not current_user.email:
                return jsonify({'success': False, 'error': 'No email address on file'}), 400
            
            subject, body = notifications.format_transcript_email(
                transcript.transcript_text,
                transcript.instagram_url,
                transcript.language,
                transcript.line_count
            )
            notifications.send_email(current_user.email, subject, body)
            transcript.sent_email = True
            db.session.commit()
            
            return jsonify({'success': True, 'message': f'Transcript sent to {current_user.email}'})
        
        elif method == 'sms':
            if not current_user.phone or not current_user.phone_carrier:
                return jsonify({
                    'success': False, 
                    'error': 'Please set your phone number and carrier in your profile'
                }), 400
            
            message = f"🎬 Transcript ready! {transcript.line_count} lines. Check your email for full text."
            notifications.send_sms(current_user.phone, current_user.phone_carrier, message)
            transcript.sent_sms = True
            db.session.commit()
            
            return jsonify({'success': True, 'message': f'SMS sent to {current_user.phone}'})
        
        elif method == 'whatsapp':
            if not current_user.whatsapp:
                return jsonify({
                    'success': False, 
                    'error': 'Please set your WhatsApp number in your profile'
                }), 400
            
            message = notifications.format_transcript_message(
                transcript.transcript_text,
                transcript.instagram_url,
                transcript.language
            )
            if len(message) > 1600:
                message = message[:1597] + "..."
            
            notifications.send_whatsapp(current_user.whatsapp, message)
            transcript.sent_whatsapp = True
            db.session.commit()
            
            return jsonify({'success': True, 'message': f'WhatsApp sent to {current_user.whatsapp}'})
        
        else:
            return jsonify({'success': False, 'error': 'Invalid delivery method'}), 400
    
    except notifications.NotificationError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to send: {str(e)}'}), 500


@app.route('/send-direct', methods=['POST'])
@login_required
def send_direct():
    """Send transcript directly to specified recipient email or WhatsApp number."""
    data = request.get_json()
    
    method = data.get('method', 'email')
    recipient = data.get('recipient', '').strip()
    transcript_id = data.get('transcript_id')
    
    if not recipient:
        return jsonify({'success': False, 'error': 'Please provide a recipient'}), 400
    
    if not transcript_id:
        return jsonify({'success': False, 'error': 'No transcript selected'}), 400
    
    # Get the transcript
    transcript = Transcript.query.filter_by(id=transcript_id, user_id=current_user.id).first()
    
    if not transcript:
        return jsonify({'success': False, 'error': 'Transcript not found'}), 404
    
    try:
        if method == 'email':
            # Validate email format
            if '@' not in recipient or '.' not in recipient:
                return jsonify({'success': False, 'error': 'Please enter a valid email address'}), 400
            
            subject, body = notifications.format_transcript_email(
                transcript.transcript_text,
                transcript.instagram_url,
                transcript.language,
                transcript.line_count
            )
            notifications.send_email(recipient, subject, body)
            transcript.sent_email = True
            db.session.commit()
            
            return jsonify({'success': True, 'message': f'Transcript sent to {recipient}'})
        
        elif method == 'whatsapp':
            # Clean phone number
            phone = ''.join(filter(str.isdigit, recipient.replace('+', '')))
            if not phone or len(phone) < 10:
                return jsonify({'success': False, 'error': 'Please enter a valid phone number with country code'}), 400
            
            if not recipient.startswith('+'):
                recipient = '+' + phone
            
            message = notifications.format_transcript_message(
                transcript.transcript_text,
                transcript.instagram_url,
                transcript.language
            )
            if len(message) > 1600:
                message = message[:1597] + "..."
            
            notifications.send_whatsapp(recipient, message)
            transcript.sent_whatsapp = True
            db.session.commit()
            
            return jsonify({'success': True, 'message': f'WhatsApp sent to {recipient}'})
        
        else:
            return jsonify({'success': False, 'error': 'Invalid delivery method'}), 400
    
    except notifications.NotificationError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to send: {str(e)}'}), 500


@app.route('/history')
@login_required
def get_history():
    """Get user's transcript history."""
    transcripts = Transcript.query.filter_by(user_id=current_user.id)\
        .order_by(Transcript.created_at.desc())\
        .limit(20)\
        .all()
    
    return jsonify({
        'success': True,
        'transcripts': [{
            'id': t.id,
            'url': t.instagram_url,
            'language': t.language,
            'line_count': t.line_count,
            'created_at': t.created_at.isoformat(),
            'sent_email': t.sent_email,
            'sent_sms': t.sent_sms,
            'sent_whatsapp': t.sent_whatsapp
        } for t in transcripts]
    })


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


# Create tables
with app.app_context():
    db.create_all()


if __name__ == '__main__':
    print("\n" + "="*50)
    print("🎬 Instagram Video Transcriber")
    print("="*50)
    print("Starting server at http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
