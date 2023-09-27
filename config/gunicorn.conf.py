"""Gunicorn *development* config file"""
import os

# Flask WSGI application path in pattern MODULE_NAME:VARIABLE_NAME
wsgi_app = "flask_server:app"
# certificate path
certfile="cert.pem"
# # key path
keyfile="key.pem"
# The granularity of Error log outputs
loglevel = "debug"
# The number of worker processes for handling requests
workers = 1 # (2* CPU) + 1
# threads = (2* os.cpu_count()) + 1
# The socket to bind
# bind = "https://127.0.0.1:8000"
# Restart workers when code changes (development only!)
reload = True
# Write access info to /var/log
accesslog = "/var/log/gunicorn/g-chat-dev.access.log"
# eror log path
errorlog = "/var/log/gunicorn/g-chat-dev.error.log"
# Redirect stdout/stderr to log file
capture_output = True
# PID file so you can easily fetch process ID
pidfile = "/var/run/gunicorn/g-chat-dev.pid"
# Daemonize the Gunicorn process (detach & enter background)
# daemon = True
# stop gunicorn worker timeout
timeout = 0