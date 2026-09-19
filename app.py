import os
import uuid
from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp

app = Flask(__name__)

DOWNLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/feedback', methods=['POST'])
def submit_feedback_api():
    data = request.json or {}
    email = data.get('email', 'Anonymous').strip()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({"success": False, "error": "Message required"}), 400
        
    # Render blocks emails on free tier, so we save feedback to a text file locally on the server
    try:
        with open("feedback_logs.txt", "a") as f:
            f.write(f"Email: {email}\nMessage: {message}\n{'-'*30}\n")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/download', methods=['POST'])
def process_download():
    data = request.json or {}
    song_query = data.get('song', '').strip()

    if not song_query:
        return jsonify({'error': 'Song required'}), 400

    uid = str(uuid.uuid4())[:8]
    outtmpl = os.path.join(DOWNLOAD_FOLDER, f'%(title)s_{uid}.%(ext)s')

    # ULTIMATE ANTI-BOT BYPASS CONFIGURATION
    ydl_opts = {
        'format': 'm4a/bestaudio/best', 
        'outtmpl': outtmpl,
        'quiet': False, 
        'no_warnings': True,
        'noplaylist': True,
        'cachedir': False,
        'nocheckcertificate': True,
        'source_address': '0.0.0.0', # Forces IPv4
        # Using iOS and TV clients to bypass the strict web/android blocks
        'extractor_args': {'youtube': ['player_client=ios,tv']}, 
    }

    # IMPORTANT: Using 'ytmsearch1:' instead of 'ytsearch1:' to pull from YouTube Music (lower bot protection)
    query = song_query if song_query.startswith("http") else f"ytmsearch1:{song_query}"

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
        print(f"YT-DLP ERROR CAUGHT: {str(e)}") 
        return jsonify({'error': str(e)}), 500

@app.route('/get-audio/<filename>')
def get_audio(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
