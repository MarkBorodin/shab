#!/usr/bin/env bash
#sudo apt-get -qq install npm virtualenv python3.6 chromium-browser
virtualenv --python=/usr/bin/python3.6 venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
