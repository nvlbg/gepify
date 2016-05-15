from flask import Flask, render_template, redirect
# import os
import youtube_dl


ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': 'static/mp3/%(id)s.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

app = Flask(__name__)

@app.route("/download/<video_id>")
def download(video_id):
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        print(ydl.download(['http://www.youtube.com/watch?v=' + video_id]))

    # return render_template('play.html', file=video_id)
    return redirect('/static/mp3/{}.mp3'.format(video_id))

# app.secret_key = os.environ.get('FLASK_SECRET_KEY')

if __name__ == "__main__":
    app.run(debug=True)
