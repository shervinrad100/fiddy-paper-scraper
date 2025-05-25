#!/bin/bash
exec > /var/log/startup-script.log 2>&1
set -ex
sudo apt-get update && sudo apt-get install -y \
    curl \
    git \
    build-essential \
    python3 \
    python3-pip \

curl -sSL https://install.python-poetry.org | python3 -
export PATH="$HOME/.local/bin:$PATH"
poetry --version

git clone https://github.com/shervinrad100/fiddy-paper-scraper.git && cd fiddy-paper-scraper

poetry install
