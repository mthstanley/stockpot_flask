"""create_app.py

creates an instance of the stockpot app for use by the flask cli tool
"""

import os
from app import create_app
app = create_app(os.getenv('FLASK_CONFIG') or 'default')
