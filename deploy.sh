#!/bin/bash

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install required packages
sudo apt-get install -y software-properties-common build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev wget

# Install Python 3.12
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3.12-dev

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies explicitly
pip install uvicorn fastapi python-dotenv httpx openai apscheduler pydantic python-jose supabase python-multipart aiohttp tenacity sqlalchemy

# Install the project
pip install -e .

# Ensure correct permissions
sudo chown -R dango:dango /home/dango/CryptoMonitoringbot
sudo chmod -R 755 /home/dango/CryptoMonitoringbot

# Copy service files
sudo cp crypto-monitor-backend.service /etc/systemd/system/
sudo cp crypto-monitor-bot.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start services
sudo systemctl enable crypto-monitor-backend
sudo systemctl enable crypto-monitor-bot
sudo systemctl start crypto-monitor-backend
sudo systemctl start crypto-monitor-bot

# Check status
echo "Backend service status:"
sudo systemctl status crypto-monitor-backend
echo "Bot service status:"
sudo systemctl status crypto-monitor-bot 