import subprocess
import shutil

# Worker process that spawns processes to transcript the media file
# Starts the engine and redirects output to a temp file (logging)
def process_job(filename, tmp_output_log_dir, speechengine='whisper', params='--model small'
                cuda_ld_library_path='LD_LIBRARY_PATH=/usr/local/cuda/targets/x86_64-linux/lib/',
                cuda_wrapper='CUDA_VISIBLE_DEVICES=0'):

    if speechengine == 'whisper':
        engine_full_command = shutil.which('whisper')

        job_command = f'{cuda_ld_library_path} {cuda_wrapper} {engine_full_command} {params} {filename}'

        print('Starting job:', job_command)
        proc = subprocess.Popen(job_command,
                                stdout=subprocess.PIPE, bufsize=1, shell=True)

        try:
            logfile = tmp_output_log_dir + '/' + 'output.log'
            print('Writing to log file:', logfile)
            with open(logfile, 'w') as tmp_output_log:
                for line in iter(proc.stdout.readline, b""):
                    print(line)
                    tmp_output_log.write(str(line) + '\n')
                    tmp_output_log.flush()

        except KeyboardInterrupt:
            proc.kill()
    else:
        print('Unsupported speech engine:', speechengine)
