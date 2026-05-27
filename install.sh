#!/usr/bin/env bash

set -e
sudo apt install build-essential python3-venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install PySide6
