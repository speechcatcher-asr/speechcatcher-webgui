import argparse

import flask
from flask import send_file
from flask import Flask, flash, request, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.serving import WSGIRequestHandler

import os
import tempfile

from redis import Redis
from rq import Queue

speechcatcher_queue = Queue(connection=Redis())

# Todo: yaml config for everything below, or as additional params to argparse
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['CUDA_WRAPPER'] = 'CUDA_VISIBLE_DEVICES=0'
app.config['CUDA_LD_LIBRARY_PATH'] = 'LD_LIBRARY_PATH=/usr/local/cuda/targets/x86_64-linux/lib/'
app.config['SPEECHENGINE'] = 'whisper'
app.config['SPEECHENGINE_PARAMS'] = '--model small'

# only for development
app.secret_key = 'secretkey'

# Upload a media file to app.config['UPLOAD_FOLDER']
# adapted from the example in the flask documentation: https://flask.palletsprojects.com/en/2.2.x/patterns/fileuploads/
# test with curl, e.g.:
# curl -i -X POST -H "Content-Type: multipart/form-data" -F "file=@Sachunterricht.mp4" http://localhost:5000/process
@app.route('/process', methods=['POST'])
def process_file():
    # check if the post request has the file part
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    # Note: might make sense to implement filter for extensions?
    if file:
        filename = secure_filename(file.filename)
        full_filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(full_filename)
        tmp_output_log_dir = tempfile.mkdtemp(prefix='speechcatcher_')

        # Queue a job for the uploaded file with a backend/asr_worker.py worker
        speechcatcher_queue.enqueue('backend.asr_worker.process_job', args=(full_filename, tmp_output_log_dir,
                                                                            app.config['SPEECHENGINE'], 
                                                                            app.config['SPEECHENGINE_PARAMS'],
                                                                            app.config['CUDA_LD_LIBRARY_PATH'],
                                                                            app.config['CUDA_WRAPPER']))

        return 'ok'

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Upload and queue server for speechcatcher jobs')
    parser.add_argument('-l', '--listen-host', default='127.0.0.1', dest='host', help='Host address to listen on.')
    parser.add_argument('-p', '--port', default=5000, dest='port', help='Port to listen on.', type=int)
    parser.add_argument('--debug', dest='debug', help='Start with debugging enabled',
                        action='store_true', default=False)

    args = parser.parse_args()

    if args.debug:
        app.debug = True

    WSGIRequestHandler.protocol_version = 'HTTP/1.1'
    app.run(host=args.host, port=args.port, threaded=True, use_reloader=False, use_debugger=False)
    #,  ssl_context='adhoc')
