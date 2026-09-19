import os
import uuid
import smtplib
import re
from email.mime.text import MIMEText
from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp

app = Flask(__name__)

DOWNLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# --- EMAIL SETTINGS ---
SENDER_EMAIL = "vkmusics23@gmail.com"
APP_PASSWORD = "ciphqvundxlpzlzs" 
ADMIN_EMAIL = "vkmusics23@gmail.com"

def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def send_search_email(song_name):
    try:
        msg = MIMEText(f"Track Search Alert:\n\nName/Link: {song_name}", 'plain', 'utf-8')
        msg['Subject'] = 'New Track Search - Vishesh Musics'
        msg['From'] = SENDER_EMAIL
        msg['To'] = ADMIN_EMAIL
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print("Email error:", e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/feedback', methods=['POST'])
def submit_feedback_api():
    data = request.json or {}
    email = data.get('email', '').strip()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({"success": False, "error": "Message required"}), 400
        
    try:
        admin_body = f"Feedback Received!\n\nEmail: {email if email else 'Anonymous'}\nMessage:\n{message}"
        admin_msg = MIMEText(admin_body, 'plain', 'utf-8')
        admin_msg['Subject'] = 'New Feedback - Vishesh Musics'
        admin_msg['From'] = SENDER_EMAIL
        admin_msg['To'] = ADMIN_EMAIL

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(admin_msg)
            
            if email and is_valid_email(email):
                user_body = f"Hello,\n\nThank you for reaching out to Vishesh Musics!\n\nWe have received your feedback:\n\"{message}\"\n\nYour support helps us make the platform better. We will look into it!\n\nBest Regards,\nVishesh Kesharwani\nCreator, Vishesh Musics"
                user_msg = MIMEText(user_body, 'plain', 'utf-8')
                user_msg['Subject'] = 'Thank You for Your Feedback! - Vishesh Musics'
                user_msg['From'] = f"Vishesh Musics <{SENDER_EMAIL}>"
                user_msg['To'] = email
                server.send_message(user_msg)
            
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/download', methods=['POST'])
def process_download():
    data = request.json or {}
    song_query = data.get('song', '').strip()

    if not song_query:
        return jsonify({'error': 'Song required'}), 400

    send_search_email(song_query)

    uid = str(uuid.uuid4())[:8]
    outtmpl = os.path.join(DOWNLOAD_FOLDER, f'%(title)s_{uid}.%(ext)s')

    # CLOUD FIX & ANTI-BOT BYPASS (THE MAGIC HAPPENS HERE)
   # CLOUD FIX & ANTI-BOT BYPASS 
    ydl_opts = {
        'format': 'm4a/bestaudio/best', 
        'outtmpl': outtmpl,
        'quiet': False, 
        'no_warnings': True,
        'noplaylist': True,
        'cachedir': False,
        'nocheckcertificate': True,
        'cookiefile': 'cookies.txt', # <--- YE LINE YOUTUBE BOT PROTECTION KO BYPASS KAREGI
        'source_address': '0.0.0.0', 
        'extractor_args': {'youtube': ['player_client=android']}, 
    }

    query = song_query if song_query.startswith("http") else f"ytsearch1:{song_query}"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            
        actual_filename = None
        for f in os.listdir(DOWNLOAD_FOLDER):
            if uid in f:
                actual_filename = f
                break
                
        if not actual_filename:
            raise Exception("Audio extraction failed on cloud server.")

        title = info.get('title', song_query) if 'info' in locals() else song_query

        return jsonify({'success': True, 'title': title, 'download_url': f'/get-audio/{actual_filename}'})
    except Exception as e:
        # Pushing the exact error to Render Logs for debugging
        print(f"YT-DLP ERROR CAUGHT: {str(e)}") 
        return jsonify({'error': str(e)}), 500

@app.route('/get-audio/<filename>')
def get_audio(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
