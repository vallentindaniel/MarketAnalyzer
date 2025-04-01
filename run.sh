#!/bin/bash

# Set default environment variables if not set
export SESSION_SECRET=${SESSION_SECRET:-"market_analyzer_secret_key"}

# Check if python-dotenv is installed
pip show python-dotenv >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Installing python-dotenv..."
    pip install python-dotenv
fi

# Check other required dependencies
REQUIRED_PACKAGES=("flask" "flask-sqlalchemy" "pandas" "numpy" "sqlalchemy" "gunicorn" "psycopg2-binary")
for package in "${REQUIRED_PACKAGES[@]}"; do
    pip show $package >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "Installing $package..."
        pip install $package
    fi
done

# Initialize database
echo "Initializing database..."
python init/db_init.py

# Run the application
echo "Starting Market Analyzer application..."
if [ "$1" = "--debug" ]; then
    # Run in debug mode
    export FLASK_DEBUG=1
    export FLASK_APP=main.py
    flask run --host=0.0.0.0 --port=5000
else
    # Run with gunicorn
    gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
fi

echo "Application stopped."