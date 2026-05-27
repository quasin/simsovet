#!/usr/bin/env bash

cd "$(dirname "$(readlink -f "$0")")"
mkdir -p data
source .venv/bin/activate
python3 main.py
