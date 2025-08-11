
#!/usr/bin/env python3
"""
Sample Python application demonstrating various imports
for dependency analysis testing.
"""

# Standard library imports
import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

# Third-party imports
import requests
import flask
from flask import Flask, request, jsonify
import sqlalchemy
from sqlalchemy import create_engine
import django
from django.conf import settings

# Conditional imports
try:
    import pandas as pd
    import numpy as np
    HAS_DATA_LIBS = True
except ImportError:
    HAS_DATA_LIBS = False

# Import with alias
import fastapi as api
from pydantic import BaseModel

# Local imports (these should be filtered out)
from .config import DATABASE_URL
from .utils import helper_function
from . import models

@dataclass
class SampleData:
    """Sample data class using various imported libraries."""
    name: str
    timestamp: datetime
    data: Optional[Dict] = None

class APIModel(BaseModel):
    """FastAPI model using Pydantic."""
    id: int
    name: str
    active: bool = True

def create_app() -> Flask:
    """Create Flask application with dependencies."""
    app = Flask(__name__)
    
    # Use imported libraries
    engine = create_engine(DATABASE_URL)
    
    @app.route('/api/data', methods=['GET', 'POST'])
    def handle_data():
        """Handle data with multiple library usage."""
        if request.method == 'POST':
            # Use requests for external API call
            response = requests.get('https://api.example.com/data')
            
            if HAS_DATA_LIBS:
                # Use pandas/numpy if available
                df = pd.DataFrame(response.json())
                processed = np.mean(df.select_dtypes(include=[np.number]))
                return jsonify({'processed': processed})
            
            return jsonify(response.json())
        
        return jsonify({'status': 'ok'})
    
    return app

def main():
    """Main application entry point."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Create sample data
    sample = SampleData(
        name="test",
        timestamp=datetime.now(),
        data={"key": "value"}
    )
    
    logger.info(f"Created sample: {sample}")
    
    # Create and run app
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == "__main__":
    main()
