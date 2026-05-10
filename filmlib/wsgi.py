import sys
import os

# Путь к директории с проектом
path = '/home/YOUR_USERNAME/pa_deploy'
if path not in sys.path:
    sys.path.append(path)

from app import app as application
