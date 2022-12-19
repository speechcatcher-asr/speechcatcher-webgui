import argparse

import flask
from flask import Flask, flash, request, redirect, url_for, send_file, jsonify
from werkzeug.utils import secure_filename
from werkzeug.serving import WSGIRequestHandler

import os
import sys
import glob
import tempfile
import yaml
import traceback

from io import BytesIO
from zipfile import ZipFile

from redis import Redis
from rq import Queue
from rq.registry import StartedJobRegistry
from rq.job import Job
from rq.command import send_stop_job_command

redis_conn = Redis()
speechcatcher_queue = Queue(connection=redis_conn)
registry = StartedJobRegistry('default', connection=redis_conn)

# Todo: yaml config for everything below, or as additional params to argparse
app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'

yaml_config = None

# only for development
app.secret_key = 'secretkey'

def load_config(config_filename='config.yaml'):
    with open(config_filename, "r") as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            traceback.print_exc()
            sys.exit(-3)

api_prefix = ''

# enqueue an ASR job on the redis job queue
def enqueue_asr_job(filename, full_filename):
    tmp_output_log_dir = tempfile.mkdtemp(prefix='speechcatcher_')
    # Queue a job for the uploaded file with a backend/asr_worker.py worker
    # Note: the default timeout is only 180 seconds in redis queue, we increase it to 100 hours.
    return speechcatcher_queue.enqueue('asr_worker.process_job', job_timeout=360000, args=(full_filename,
                                                                            tmp_output_log_dir,
                                                                            yaml_config['speechengine'],
                                                                            yaml_config['speechengine_params'],
                                                                            yaml_config['cuda_ld_library_path'],
                                                                            yaml_config['cuda_wrapper']),
                                                                            description=filename)

# enqueue a download job on the redis job queue
def enqueue_download_job(url):
    return speechcatcher_queue.enqueue('asr_worker.download_video', job_timeout=360000, args=(url,), description=url)

# Upload a media file to yaml_config['upload_folder']
# adapted from the example in the flask documentation: https://flask.palletsprojects.com/en/2.2.x/patterns/fileuploads/
# test with curl, e.g.:
# curl -i -X POST -H "Content-Type: multipart/form-data" -F "my_file=@Sachunterricht.mp4" http://localhost:5000/process
@app.route(api_prefix+'/process', methods=['POST'])
def process_file():
    # check if the post request has the file part
    if 'my_file' not in request.files:
        print('Warning: No file part')
        return '<p>Error: no file part</p>'
    
    # TODO: allow multiple files
    file = request.files['my_file']
    print(f'{file=}')
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        print('Warning: No selected file')
        return '<p>Error: no selected file</p>'
    # Note: might make sense to implement filter for extensions?
    if file:
        filename = secure_filename(file.filename)
        full_filename = os.path.join(yaml_config['upload_folder'], filename)
        file.save(full_filename)
        tmp_output_log_dir = tempfile.mkdtemp(prefix='speechcatcher_')

        enqueue_asr_job(filename, full_filename)

        return '<p>File uploaded.</p>'
    else:
        return '<p>Error: no file object</p>'

# process url to a video
@app.route(api_prefix+'/process_url', methods=['POST'])
def process_url():
    print('request form: ', request.form)
    url = request.form['url']
    enqueue_download_job(url)    
    return '<p>Download job started.</p>'

# Helper function to extract the most important information about a job that is displayed to the user
def get_job_status_dict(job):
    return {'jobid': job.id,'description':job.description, 'status':job.get_status(), 'enqueued_at':job.enqueued_at,
            'started_at':job.started_at, 'ended_at':job.ended_at, 
            'progress_percent':job.meta['progress_percent'] if 'progress_percent' in job.meta else 0.0,
            'progress_status':job.meta['progress_status'] if 'progress_status' in job.meta else 'Loading job...'}

# List the status of all running, queued and expired jobs as json
@app.route(api_prefix+'/status', methods=['GET'])
def status():
    running_job_ids = registry.get_job_ids() 
    expired_job_ids = registry.get_expired_job_ids() 
    queued_job_ids = registry.get_queue().job_ids

    running_jobs = Job.fetch_many(running_job_ids, connection=redis_conn)
    running_job_dicts = [get_job_status_dict(job) for job in running_jobs]

    expired_jobs = Job.fetch_many(expired_job_ids, connection=redis_conn)
    expired_job_dicts = [get_job_status_dict(job) for job in expired_jobs]

    queued_jobs = Job.fetch_many(queued_job_ids, connection=redis_conn)
    queued_job_dicts = [get_job_status_dict(job) for job in queued_jobs]

    return jsonify({'running': running_job_dicts, 'expired': expired_job_dicts,
                     'queued': queued_job_dicts})

# Cancel job endpoint
@app.route(api_prefix+'/cancel_job/<job_id>', methods=['GET'])
def cancel_job(job_id):
    job = Job.fetch(job_id, connection=redis_conn)
    job.cancel()
    return 'ok'

# Kill a running job (cancelling is only valid for queued jobs)
@app.route(api_prefix+'/kill_job/<job_id>', methods=['GET'])
def kill_job(job_id):
    send_stop_job_command(redis_conn, job_id)
    return 'ok'

# List available and finished transcriptions that the user can download
# We let the speechengine write to all formats (srt, txt, vtt), but only search with *.vtt
@app.route(api_prefix+'/list_outputs', methods=['GET'])
def list_outputs():
    folder_len = len(yaml_config['output_folder'])
    vtts = glob.glob(yaml_config['output_folder'] + '*.vtt')
    base_filenames = [myfile[folder_len:-4] for myfile in vtts]
    return jsonify(base_filenames)

@app.route(api_prefix+'/zip_files/<file_format>')
def zip_files(file_format):

    assert(file_format in ["vtt", "srt", "txt"])
    
    buffer = BytesIO()

    # Open a ZipFile object in memory and add all files with <file_format> in output_folder
    with ZipFile(buffer, 'w') as zip_file:
        for filename in os.listdir(yaml_config['output_folder']):
            if filename.endswith('.'+file_format):
                zip_file.write(yaml_config['output_folder']+filename)

    buffer.seek(0)
    return send_file(buffer, download_name=f'{file_format}_files.zip', as_attachment=True)

# Create directory if it doesnt exist
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

    yaml_config = load_config(config_filename='config.yaml')

    ensure_dir(yaml_config['upload_folder'])
    ensure_dir(yaml_config['output_folder'])

    if args.debug:
        app.debug = True

    WSGIRequestHandler.protocol_version = 'HTTP/1.1'
    app.run(host=args.host, port=args.port, threaded=True, use_reloader=False, use_debugger=False)
    #,  ssl_context='adhoc')
