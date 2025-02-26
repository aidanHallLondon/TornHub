#!/bin/bash

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install it before proceeding."
    exit 1
fi

# Check for pip
if ! command -v pip &> /dev/null; then
    echo "Error: pip is not installed. Please install it before proceeding."
    exit 1
fi

# Create and activate the virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Determine the operating system
OS=$(uname -s)

if [[ "$OS" == "Darwin" ]]; then  # macOS
    echo "Installing dependencies on macOS..."
    brew install db-browser-for-sqlite graphviz
    brew install graphviz
    pip install beautifulsoup4
    pip install matplotlib
    pip install paramiko
elif [[ "$OS" == "Linux" ]]; then
    echo "Installing dependencies on Linux..."
    # Replace with your Linux distribution's package manager (e.g., apt, yum, dnf)
    sudo apt-get update
    sudo apt-get install -y sqlitebrowser graphviz
    sudo apt-get install graphviz 
    sudo apt-get install beautifulsoup4
    sudo apt-get install matplotlib
    sudo apt-get install paramiko
elif [[ "$OS" == "Windows" ]]; then
    echo "Installing dependencies on Windows..."
    # Provide instructions or a script for Windows installations
    echo "  Please download and install the following:"
    echo "    * DB Browser for SQLite: https://sqlitebrowser.org/dl/"
    echo "    * Graphviz: https://graphviz.org/download/"
    echo "    * beautifulsoup4"
    echo "    * matplotlib"
    echo "    * paramiko"
else
    echo "Unsupported operating system: $OS"
fi

# you can run TornHub scripts with the api key as an argument
# python3 initialise.py --api_key=??????????????
python3 initialise.py

python3 generateSchema.py


echo "Done!"