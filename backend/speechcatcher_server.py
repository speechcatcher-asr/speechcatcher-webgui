import argparse

import flask
from flask import Flask, flash, request, redirect, url_for, send_file, jsonify
from werkzeug.utils import secure_filename
from werkzeug.serving import WSGIRequestHandler

import os
import tempfile

from redis import Redis
from rq import Queue
from rq.registry import StartedJobRegistry
from rq.job import Job

redis_conn = Redis()
speechcatcher_queue = Queue(connection=redis_conn)
registry = StartedJobRegistry('default', connection=redis_conn)

# Todo: yaml config for everything below, or as additional params to argparse
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['CUDA_WRAPPER'] = '' #'CUDA_VISIBLE_DEVICES=0'
app.config['CUDA_LD_LIBRARY_PATH'] = '' #'LD_LIBRARY_PATH=/usr/local/cuda/targets/x86_64-linux/lib/'
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
    #if len(request.files) == 0:
    if 'my_file' not in request.files:
        print('Warning: No file part')
        return 'error: no file part' #redirect(request.url)
    
    # TODO: allow multiple files
    file = request.files['my_file']
    print(f'{file=}')
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    #if file.filename == '':
    #    print('Warning: No selected file')
    #    return 'error: no selected file' #redirect(request.url)
    # Note: might make sense to implement filter for extensions?
    if file:
        filename = secure_filename(file.filename)
        full_filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(full_filename)
        tmp_output_log_dir = tempfile.mkdtemp(prefix='speechcatcher_')

        # Queue a job for the uploaded file with a backend/asr_worker.py worker
        speechcatcher_queue.enqueue('asr_worker.process_job', args=(full_filename, tmp_output_log_dir,
                                                                            app.config['SPEECHENGINE'], 
                                                                            app.config['SPEECHENGINE_PARAMS'],
                                                                            app.config['CUDA_LD_LIBRARY_PATH'],
                                                                            app.config['CUDA_WRAPPER']), description=filename)

        return '<p>File uploaded.</p>'

def get_job_status_dict(job):
    return {'description':job.description, 'status':job.get_status, 'enqueued_at':job.enqueued_at,
            'started_at':job.started_at, 'ended_at':job.ended_at}

@app.route('/status', methods=['GET'])
def status():
    running_job_ids = registry.get_job_ids() 
    expired_job_ids = registry.get_expired_job_ids() 
    queued_job_ids = registry.get_queue().job_ids

    running_jobs = Job.fetch_many(running_job_ids, connection=redis)
    running_job_dicts = [get_job_status_dict(job) for job in running_jobs]

    expired_jobs = Job.fetch_many(expired_job_ids, connection=redis)
    expired_job_dicts = [get_job_status_dict(job) for job in expired_jobs]

    queued_jobs = Job.fetch_many(queued_job_ids, connection=redis)
    queued_job_dicts = [get_job_status_dict(job) for job in queued_jobs]

    return jsonify({'running': running_job_dicts, 'expired': expired_job_dicts,
                     'queued': queued_job_dicts})

@app.route('/list_outputs', methods=['GET'])
def list_outputs():
    folder_len = len(app.config['UPLOAD_FOLDER'])
    vtts = glob.glob(app.config['UPLOAD_FOLDER'] + '*.vtt')
    base_filenames = [myfile[folder_len:-4] for myfile in vtts]
    return jsonify(base_filenames)

def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Upload and queue server for speechcatcher jobs')
    parser.add_argument('-l', '--listen-host', default='127.0.0.1', dest='host', help='Host address to listen on.')
    parser.add_argument('-p', '--port', default=6000, dest='port', help='Port to listen on.', type=int)
    parser.add_argument('--debug', dest='debug', help='Start with debugging enabled',
                        action='store_true', default=False)

    args = parser.parse_args()

    ensure_dir(app.config['UPLOAD_FOLDER'])

    if args.debug:
        app.debug = True

    WSGIRequestHandler.protocol_version = 'HTTP/1.1'
    app.run(host=args.host, port=args.port, threaded=True, use_reloader=False, use_debugger=False)
    #,  ssl_context='adhoc')
