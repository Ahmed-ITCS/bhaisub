from flask import Flask, request, send_file, render_template, after_this_request
import subprocess
import os
import whisper  # Using the local whisper library

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    file = request.files['video']
    video_path = 'input.mp4'
    audio_path = 'audio.mp3'
    subtitle_path = 'subtitles.srt'
    output_path = 'output.mp4'
    file.save(video_path)

    # Step 1: Extract audio
    subprocess.run(['ffmpeg', '-i', video_path, '-q:a', '0', '-map', 'a', audio_path])

    # Step 2: Transcribe using local Whisper model
    model = whisper.load_model("base")  # You can choose "tiny", "base", "small", "medium", or "large"
    result = model.transcribe(audio_path)
    text = result["text"]

    # Step 3: Generate proper .srt file with timestamps
    segments = result["segments"]
    with open(subtitle_path, 'w') as f:
        for i, segment in enumerate(segments):
            start_time = format_timestamp(segment["start"])
            end_time = format_timestamp(segment["end"])
            f.write(f"{i+1}\n{start_time} --> {end_time}\n{segment['text'].strip()}\n\n")

    # Step 4: Burn subtitles into video
    subprocess.run([
        'ffmpeg', '-i', video_path,
        '-vf', f"subtitles={subtitle_path}",
        output_path
    ])

    @after_this_request
    def cleanup(response):
        # Delete all temporary files
        for file_path in [video_path, audio_path, subtitle_path, output_path]:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Deleted {file_path}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
        return response

    return send_file(output_path, as_attachment=True)

def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    hours = int(seconds / 3600)
    seconds %= 3600
    minutes = int(seconds / 60)
    seconds %= 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

if __name__ == '__main__':
    app.run(debug=True)
