#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI configuration for Wedos hosting
"""

import sys
import os

# Add your project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

# WSGI callable
application = app

if __name__ == "__main__":
    application.run()