#!/bin/bash

# Make sure Python packages are installed
pip install -r requirements_list.txt

# Initialize the database
python init/db_init.py

# Start the application
gunicorn --bind 0.0.0.0:5000 --reload main:app