from flask import Flask, render_template, request, jsonify, send_file
import os
import yt_dlp
import threading
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

DOWNLOAD_FOLDER = 'downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

progress = {}
video_details = {}
download_paths = {}

def update_progress(d, progress_id):
    if d['status'] == 'downloading':
        progress[progress_id] = d['_percent_str'].strip().replace('%', '')
    elif d['status'] == 'finished':
        progress[progress_id] = '100'

def fetch_video_info(url, progress_id):
    try:
        progress[progress_id] = '10'
        ydl_opts = {'quiet': True, 'noplaylist': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            progress[progress_id] = '50'
            info = ydl.extract_info(url, download=False)
            progress[progress_id] = '100'
            video_details[progress_id] = {
                "title": info.get("title", "Unknown Title"),
                "thumbnail": info.get("thumbnail", ""),
            }
    except Exception:
        video_details[progress_id] = None

def download_video(url, progress_id):
    try:
        ydl_opts = {
            'format': 'best', 
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: update_progress(d, progress_id)],
            'quiet': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            download_paths[progress_id] = filename
    except Exception:
        progress[progress_id] = '0'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch_info', methods=['POST'])
def fetch_info():
    url = request.form['video_url']
    progress_id = secrets.token_hex(8)
    threading.Thread(target=fetch_video_info, args=(url, progress_id)).start()
    return jsonify({"progress_id": progress_id})

@app.route('/get_info/<progress_id>')
def get_info(progress_id):
    return jsonify(video_details.get(progress_id, {}))

@app.route('/download', methods=['POST'])
def download():
    url = request.form['video_url']
    progress_id = secrets.token_hex(8)
    threading.Thread(target=download_video, args=(url, progress_id)).start()
    return jsonify({"progress_id": progress_id})

@app.route('/progress/<progress_id>')
def get_progress(progress_id):
    return jsonify({"progress": progress.get(progress_id, '0')})

@app.route('/serve_file/<progress_id>')
def serve_file(progress_id):
    file_path = download_paths.get(progress_id)
    if file_path and os.path.isfile(file_path):
        return send_file(file_path, as_attachment=True)
    return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True)
