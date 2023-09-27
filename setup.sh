#!/usr/bin/bash
# comment out if this is the first time enabling system daemons
sudo systemctl stop nginx.service

case $1 in 
	dev)
	echo setting up dev...
	sudo systemctl stop g-chat-dev.socket
	sudo systemctl stop g-chat-dev.service
	# copy nginx dev config
	# sudo cp config/dev/projectx-dev.conf /etc/nginx/sites-available/
	# # enable the config
	# sudo ln -s /etc/nginx/sites-available/projectx-dev.conf /etc/nginx/sites-enabled/projectx-dev.conf
	# # copy gunicorn systemd daemons
	# sudo cp config/dev/gunicorn-dev.service /etc/systemd/system/
	# sudo cp config/dev/gunicorn-dev.socket /etc/systemd/system/
	;;
	local)
	echo setting up local...
	sudo systemctl stop g-chat-local.socket
	sudo systemctl stop g-chat-local.service
	# nginx changes
	sudo cp config/local/g-chat-local.conf /etc/nginx/sites-available/
	# enable the config
	sudo ln -s /etc/nginx/sites-available/g-chat-local.conf /etc/nginx/sites-enabled/g-chat-local.conf
	# copy gunicorn systemd daemons
	sudo cp config/local/g-chat-local.service /etc/systemd/system/
	sudo cp config/local/g-chat-local.socket /etc/systemd/system/

	# create directory to hold static index.html
	mkdir /var/www/g-chat
	sudo cp index.html /var/www/g-chat/
	# commands to start services
	sudo systemctl daemon-reload
	sudo systemctl enable --now g-chat-local.socket
	sudo systemctl enable nginx.service
	sudo systemctl start nginx
	sudo systemctl start g-chat-local.socket
	;;
	*)
	echo Unrecognized command line argument. Please use 'dev' or 'local'
esac
