import os
import uuid
from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp
from ytmusicapi import YTMusic

app = Flask(__name__)
# Initialize the official YouTube Music API for safe searching
ytmusic = YTMusic()

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
        
    try:
        # Saving locally to avoid Render's SMTP email block
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

    query_url = song_query
    title = song_query
    
    # MAGIC FIX: Search using ytmusicapi instead of yt-dlp to bypass HTML bot blocks
    if not song_query.startswith("http"):
        try:
            search_results = ytmusic.search(song_query, filter="songs")
            if not search_results:
                return jsonify({'error': 'Song not found on YouTube Music.'}), 404
            
            video_id = search_results[0]['videoId']
            title = search_results[0].get('title', song_query)
            query_url = f"https://www.youtube.com/watch?v={video_id}"
        except Exception as e:
            return jsonify({'error': f"Safe Search failed: {str(e)}"}), 500

    uid = str(uuid.uuid4())[:8]
    outtmpl = os.path.join(DOWNLOAD_FOLDER, f'%(title)s_{uid}.%(ext)s')

    # Now yt-dlp ONLY downloads the direct link using the strongest anti-bot client
    ydl_opts = {
        'format': 'm4a/bestaudio/best', 
        'outtmpl': outtmpl,
        'quiet': False, 
        'no_warnings': True,
        'noplaylist': True,
        'cachedir': False,
        'nocheckcertificate': True,
        'extractor_args': {'youtube': ['player_client=android_creator']}, 
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query_url, download=True)
            
        actual_filename = None
        for f in os.listdir(DOWNLOAD_FOLDER):
            if uid in f:
                actual_filename = f
                break
                
        if not actual_filename:
            raise Exception("Audio extraction failed on cloud server.")

        final_title = info.get('title', title) if 'info' in locals() else title

        return jsonify({'success': True, 'title': final_title, 'download_url': f'/get-audio/{actual_filename}'})
    except Exception as e:
        print(f"YT-DLP ERROR CAUGHT: {str(e)}") 
        return jsonify({'error': str(e)}), 500

@app.route('/get-audio/<filename>')
def get_audio(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
