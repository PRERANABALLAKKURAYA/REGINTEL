#!/usr/bin/env python
import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Run uvicorn
import subprocess
result = subprocess.run(
    [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd=os.path.dirname(os.path.abspath(__file__))
)
sys.exit(result.returncode)
