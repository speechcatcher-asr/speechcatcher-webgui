# Speechcatcher-webgui

Speechcatcher-webgui is a web based GUI for automatic transcription and subtitling engines. It supports speech recognition models like <a href="https://github.com/speechcatcher-asr/speechcatcher">speechcatcher (CPU)</a> and <a href="https://github.com/openai/whisper">whisper (GPU)</a>.

![Speechcatcher screenshot](https://github.com/speechcatcher-asr/speechcatcher-webgui/raw/main/screenshot1.png)

## Installation

It is recommended to run Speechcatcher-webgui natively on a server or workstation. Espacially if you plan on using GPU acceleration, virtualization will usually make your setup needlessly complicated.  

The first step is cloning this repository:

```
git clone https://github.com/speechcatcher-asr/speechcatcher-webgui
```

### Frontend

Npm is used for all Javascript dependencies. To install them, simply do:

```
cd frontend
npm install
```

Note: currently 'npm run' isn't linked, as speechcatcher-webgui is still in development. The weppage directly references the scripts in the "node\_modules/" directory. This will be changed for a production installation at a later stage.

### Backend and Python packages

First create a virtual environment for the backend and activate it, then you can install required packages with pip:

```
cd backend/
virtualenv -p python3.10 backend_env
source backend_env/bin/activate
pip3 install -r requirements.txt
```

Note: currently we used the integrated flask server for development purposes, but this will be changed to a production server (like gunicorn) at a later stage of this project.

### Nginx webserver

Speechcatcher-webgui uses nginx to serve static content and also uses it to reverse proxy the backend. 

In a typical debian/ubuntu based distrbution you can install nginx with:

```
sudo apt-get install nginx
``` 

Then you can copy the sample config file.

```
cp speechcatcher_nginx_sample.conf /etc/nginx/sites-available/speechcatcher.conf
```

make some changes to /etc/nginx/sites-available/speechcatcher.conf, **at the very least configure the root directory to match your frontend installation**. Then make a link:

```
ln -s /etc/nginx/sites-available/speechcatcher.conf /etc/nginx/sites-enabled/speechcatcher.conf
``` 

You can now restart the nginx server:

```
sudo service restart nginx
```

# Starting the backend

When you start the backend server make sure that you are in the correct virtual environment and in the backend directory:

```
source backend_env/bin/activate
cd backend
python3 speechcatcher_server.py
```

in a new screen or window, start the rqworker service:

```
rqworker
```

On newer versions of Mac OS X you might need to do: 

```
OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES rqworker
```

So that rqworker doesn't crash on trying to fork.

# That's it!

You should now be able to see and use the webgui on http://localhost/
