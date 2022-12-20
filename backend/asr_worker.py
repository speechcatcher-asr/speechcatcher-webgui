import subprocess
import shutil
import os
import requests
import re
from rq import get_current_job

from yt_dlp import YoutubeDL

def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)

# inspired by https://stackoverflow.com/questions/31024968/using-ffmpeg-to-obtain-video-durations-in-python
def get_duration(input_video):
    cmd = ['ffprobe', '-i', input_video, '-show_entries', 'format=duration', '-v', 'quiet', '-sexagesimal', '-of', 'csv=p=0']
    return subprocess.check_output(cmd).decode("utf-8").strip()

# https://stackoverflow.com/questions/23727943/how-to-get-information-from-youtube-dl-in-python
def download_video_progress_hook(response):
    myjob = get_current_job()
    downloaded_percent = 0
    if response['total_bytes'] > 0:
        downloaded_percent = (response['downloaded_bytes']*100.0)/response['total_bytes']
    myjob.meta['progress_percent'] = downloaded_percent
    myjob.meta['progress_status'] = response['status']
    myjob.save_meta()

# Downloads a video (or media file) with yt_dlp    
def download_video(url, api_url='http://localhost/sc/apiv1/'):
    ydl_opts = {'progress_hooks': [download_video_progress_hook]}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # Get the filename using the extract filename method, see https://github.com/ytdl-org/youtube-dl/issues/13750
        filename = ydl.prepare_filename(info)
        print('Downloaded file:', filename)

        ensure_dir('downloads/')
        dest_filename = 'downloads/' + filename 
        shutil.move(filename, dest_filename)

        response = requests.post(url, params={'filename':filename, 'full_filename':dest_filename})
        r = requests.get(api_url + 'process_local')

        return filename

# Extract total number of seconds, timestamp can be in either "HH:MM:SS.fff" or "MM:SS.fff"
def convert_to_seconds(timestamp):
    #extract parts: 12:34.567 -> ["12","34","567"]
    # or 12:34:56.789 -> ["12", "34", "56", "789"]
    parts = timestamp.replace('.',':').split(':')

    if len(parts) == 4:
        hours, minutes, seconds, milliseconds = int(parts[0]), int(parts[1]), int(parts[2]), parts[3]
    elif len(parts) == 3:
        hours, minutes, seconds, milliseconds = 0, int(parts[0]), int(parts[1]), parts[2]
    else:
        print('warning, unsupported timestamp:', timestamp)
        return 0.0

    # in case of HH:MM:SS.fffff, only take the three leading digits fff for miliseconds
    milliseconds = int(milliseconds[:3])

    # return the total number of seconds
    return hours * 3600.0 + minutes * 60.0 + seconds + milliseconds / 1000.0

#timestamp_regular_expression = r'\[(\d?\d?:?\d\d:\d\d\.\d\d\d)\s*-->\s*(\d?\d?:?\d\d:\d\d\.\d\d\d)\]' 
timestamp_regular_expression = r'\[(\d*:?\d*:\d*\.\d*)\s*-->\s*(\d*:?\d*:\d*\.\d*)\]'

# Worker process that spawns processes to transcript the media file
# Starts the engine and redirects output to a temp file (logging)
def process_job(filename, tmp_output_log_dir, speechengine='whisper', params='--model small',
                cuda_ld_library_path='LD_LIBRARY_PATH=/usr/local/cuda/targets/x86_64-linux/lib/',
                cuda_wrapper='CUDA_VISIBLE_DEVICES=0'):

    myjob = get_current_job()
    media_duration = get_duration(filename)
    media_duration_seconds = convert_to_seconds(media_duration)
    print(f'{media_duration=}, {media_duration_seconds=}')

    myjob.meta['media_duration'] = media_duration
    myjob.meta['media_duration_seconds'] = media_duration_seconds
    myjob.save_meta()

    if speechengine == 'whisper':
        engine_full_command = shutil.which('whisper')

        job_command = f'{cuda_ld_library_path} {cuda_wrapper} {engine_full_command} {params} {filename}'.strip()

        print('Starting job:', job_command)
        
        myjob.meta['progress_percent'] = 0
        myjob.meta['progress_status'] = 'Loading model...'
        myjob.save_meta()

        proc = subprocess.Popen(job_command, bufsize=1, stdout=subprocess.PIPE, shell=True)

        try:
            logfile = tmp_output_log_dir + '/' + 'output.log'
            print('Writing to log file:', logfile)
            with open(logfile, 'w') as tmp_output_log:
                for line in iter(proc.stdout.readline, b""):
                    print(line)
                    line_str = str(line)
                    if '-->' in line_str:
                        myjob.meta['progress_status'] = 'Transcribing...'
                        timestamps = re.findall(timestamp_regular_expression, line_str)[0]
                        
                        if len(timestamps) == 2:
                            start_time, end_time = timestamps[0], timestamps[1]
                            
                            print('Found timestamps:', f'{start_time=}', f'{end_time=}')
                            progress_seconds = convert_to_seconds(end_time)
                            print(f'{progress_seconds=}')
                            myjob.meta['progress_seconds'] = progress_seconds

                            if media_duration_seconds == 0:
                                progress_percent = 100.
                            else:
                                progress_percent = (progress_seconds / media_duration_seconds) * 100.
                           
                            progress_percent = min(progress_percent, 100.)
                     
                            myjob.meta['progress_percent'] = progress_percent
                            print(f'{progress_percent=}')

                            myjob.save_meta() 
                        else:
                            print('warning: could not parse timestamp:', timestamps)
                

                    tmp_output_log.write(str(line) + '\n')
                    tmp_output_log.flush()

        except KeyboardInterrupt:
            proc.kill()
    else:
        print('Unsupported speech engine:', speechengine)
