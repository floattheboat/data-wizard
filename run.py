#!/usr/bin/env python3
"""Entry point for Data Wizard application."""

import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_wizard.app import main

if __name__ == "__main__":
    main()
