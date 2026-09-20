import os
import re
import uuid
import smtplib

from flask import Flask, render_template, request, jsonify, send_from_directory
import yt_dlp
import imageio_ffmpeg

from email.mime.text import MIMEText


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

# =========================================================
# FOLDERS
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, "downloads")

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# FFmpeg bundled with imageio-ffmpeg
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================
# IMPORTANT:
# Do NOT put Gmail password directly in this file.
# These values will be added in Render Environment Variables.

SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")

ADMIN_ID = os.getenv("ADMIN_ID", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")


# =========================================================
# SIMPLE VIEW COUNTER
# =========================================================

VIEW_COUNT = 0


# =========================================================
# EMAIL VALIDATION
# =========================================================

def is_valid_email(email):
    if not email:
        return False

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.match(pattern, email) is not None


# =========================================================
# SEND SEARCH EMAIL
# =========================================================

def send_search_email(song_name):

    # If email settings are not configured,
    # don't crash the application.
    if not SENDER_EMAIL or not APP_PASSWORD or not ADMIN_EMAIL:
        print("Email settings are not configured.")
        return False

    try:

        subject = "🎵 New Song Search - Vishesh Musics"

        body = f"""
A new song search was made on Vishesh Musics.

Song / URL:
{song_name}
"""

        msg = MIMEText(body)

        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = ADMIN_EMAIL

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:

            server.login(
                SENDER_EMAIL,
                APP_PASSWORD
            )

            server.sendmail(
                SENDER_EMAIL,
                ADMIN_EMAIL,
                msg.as_string()
            )

        print("Search email sent successfully.")
        return True

    except Exception as e:

        print("Search email error:", e)
        return False


# =========================================================
# SEND FEEDBACK EMAIL
# =========================================================

def send_feedback_email(
    name,
    email,
    message,
    send_thank_you=False
):

    if not SENDER_EMAIL or not APP_PASSWORD or not ADMIN_EMAIL:
        print("Email settings are not configured.")
        return False

    try:

        # -------------------------------------------------
        # ADMIN EMAIL
        # -------------------------------------------------

        admin_subject = "💬 New Feedback - Vishesh Musics"

        admin_body = f"""
New feedback received from Vishesh Musics.

Name:
{name}

Email:
{email}

Message:
{message}
"""

        admin_msg = MIMEText(admin_body)

        admin_msg["Subject"] = admin_subject
        admin_msg["From"] = SENDER_EMAIL
        admin_msg["To"] = ADMIN_EMAIL

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465
        ) as server:

            server.login(
                SENDER_EMAIL,
                APP_PASSWORD
            )

            server.sendmail(
                SENDER_EMAIL,
                ADMIN_EMAIL,
                admin_msg.as_string()
            )

            # -------------------------------------------------
            # THANK YOU EMAIL
            # -------------------------------------------------

            if (
                send_thank_you
                and email
                and is_valid_email(email)
            ):

                thank_you_subject = (
                    "❤️ Thank You for Your Feedback - Vishesh Musics"
                )

                thank_you_body = f"""
Hi {name or 'there'},

Thank you for sharing your valuable feedback
with Vishesh Musics.

We really appreciate your time and support.

Keep listening 🎵

Regards,
Vishesh Musics
"""

                thank_you_msg = MIMEText(
                    thank_you_body
                )

                thank_you_msg["Subject"] = thank_you_subject
                thank_you_msg["From"] = SENDER_EMAIL
                thank_you_msg["To"] = email

                server.sendmail(
                    SENDER_EMAIL,
                    email,
                    thank_you_msg.as_string()
                )

        print("Feedback email processed successfully.")
        return True

    except Exception as e:

        print("Feedback email error:", e)
        return False


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    global VIEW_COUNT

    VIEW_COUNT += 1

    return render_template("index.html")


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route("/api/admin/login", methods=["POST"])
def admin_login():

    try:

        data = request.get_json(silent=True) or {}

        admin_id = str(
            data.get("id", "")
        ).strip()

        password = str(
            data.get("password", "")
        )

        # Check credentials from Environment Variables
        if (
            ADMIN_ID
            and ADMIN_PASSWORD
            and admin_id == ADMIN_ID
            and password == ADMIN_PASSWORD
        ):

            return jsonify({
                "success": True,
                "views": VIEW_COUNT
            })

        return jsonify({
            "success": False,
            "message": "Invalid admin credentials."
        }), 401

    except Exception as e:

        print("Admin login error:", e)

        return jsonify({
            "success": False,
            "message": "Admin login failed."
        }), 500


# =========================================================
# FEEDBACK API
# =========================================================

@app.route("/api/feedback", methods=["POST"])
def feedback():

    try:

        data = request.get_json(silent=True) or {}

        name = str(
            data.get("name", "")
        ).strip()

        email = str(
            data.get("email", "")
        ).strip()

        message = str(
            data.get("message", "")
        ).strip()

        if not message:

            return jsonify({
                "success": False,
                "message": "Feedback message is required."
            }), 400

        send_thank_you = (
            bool(email)
            and is_valid_email(email)
        )

        send_feedback_email(
            name,
            email,
            message,
            send_thank_you
        )

        return jsonify({
            "success": True,
            "message": "Thank you for your feedback!"
        })

    except Exception as e:

        print("Feedback API error:", e)

        return jsonify({
            "success": False,
            "message": "Unable to process feedback."
        }), 500


# =========================================================
# DOWNLOAD API
# =========================================================

@app.route("/api/download", methods=["POST"])
def download_audio():

    try:

        data = request.get_json(silent=True) or {}

        song_query = str(
            data.get("song", "")
        ).strip()

        # -------------------------------------------------
        # VALIDATION
        # -------------------------------------------------

        if not song_query:

            return jsonify({
                "success": False,
                "message": "Please enter a song name or YouTube URL."
            }), 400

        # -------------------------------------------------
        # SEND SEARCH EMAIL
        # -------------------------------------------------

        send_search_email(song_query)

        # -------------------------------------------------
        # UNIQUE ID
        # -------------------------------------------------

        uid = str(
            uuid.uuid4()
        )[:8]

        outtmpl = os.path.join(
            DOWNLOAD_FOLDER,
            f"%(title)s_{uid}.%(ext)s"
        )

        # -------------------------------------------------
        # YT-DLP OPTIONS
        # -------------------------------------------------

        ydl_opts = {

            "format": "bestaudio/best",

            "outtmpl": outtmpl,

            "quiet": False,

            "no_warnings": True,

            "noplaylist": True,

            "cachedir": False,

            "ffmpeg_location": FFMPEG_PATH,

            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192"
                }
            ]
        }

        # -------------------------------------------------
        # SONG NAME OR URL
        # -------------------------------------------------

        if song_query.startswith("http://") or \
           song_query.startswith("https://"):

            query = song_query

        else:

            query = f"ytsearch1:{song_query}"

        # -------------------------------------------------
        # DOWNLOAD
        # -------------------------------------------------

        print("Starting download:", query)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                query,
                download=True
            )

        # -------------------------------------------------
        # FIND CREATED MP3
        # -------------------------------------------------

        downloaded_file = None

        for filename in os.listdir(DOWNLOAD_FOLDER):

            if filename.endswith(
                ".mp3"
            ) and uid in filename:

                downloaded_file = filename
                break

        # -------------------------------------------------
        # FILE NOT FOUND
        # -------------------------------------------------

        if not downloaded_file:

            return jsonify({
                "success": False,
                "message": "MP3 file was not created."
            }), 500

        # -------------------------------------------------
        # TITLE
        # -------------------------------------------------

        title = info.get(
            "title",
            "Downloaded Song"
        )

        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return jsonify({

            "success": True,

            "title": title,

            "download_url":
                f"/get-audio/{downloaded_file}"

        })

    except Exception as e:

        print("Download error:", repr(e))

        error_message = str(e)

        # -------------------------------------------------
        # FRIENDLY YOUTUBE MESSAGE
        # -------------------------------------------------

        if (
            "Sign in to confirm" in error_message
            or "not a bot" in error_message
        ):

            return jsonify({

                "success": False,

                "message":
                    "YouTube is currently requiring "
                    "additional verification for this request. "
                    "Please try another supported source or "
                    "try again later."

            }), 503

        # -------------------------------------------------
        # GENERIC ERROR
        # -------------------------------------------------

        return jsonify({

            "success": False,

            "message":
                "Unable to download this song right now."

        }), 500


# =========================================================
# SERVE DOWNLOADED MP3
# =========================================================

@app.route("/get-audio/<path:filename>")
def get_audio(filename):

    return send_from_directory(
        DOWNLOAD_FOLDER,
        filename,
        as_attachment=True
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return jsonify({
        "status": "ok"
    })


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
