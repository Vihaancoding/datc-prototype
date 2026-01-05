#!/bin/bash

echo "Starting DATC..."

cd ~/PycharmProjects/PythonProject2
source venv1/bin/activate

python app.py &
sleep 2

cloudflared tunnel run datc-tunnel

