#!/usr/bin/env python3.10
# -*- coding: utf-8 -*-
"""
WSGI configuration for PythonAnywhere hosting - Python 3.10
Place this file in /var/www/ directory on PythonAnywhere
Recommended Python version: 3.10
"""

import sys
import os

# Add your project directory to Python path (adjust path as needed)
# Example: if your code is in /home/yourusername/hueppe/
project_home = '/home/yourusername/hueppe'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Change working directory
os.chdir(project_home)

# Import Flask app
from app import app as application

# For debugging (remove in production)
if __name__ == "__main__":
    application.run(debug=True)