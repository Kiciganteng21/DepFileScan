"""
Sample Python file demonstrating various import patterns
for dependency analysis testing
"""

# Standard library imports
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Third-party imports
import requests
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String
from pydantic import BaseModel, Field

# Local imports
from .models import User, Product
from .utils import calculate_score, format_response
from . import config

# Conditional imports
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Import with alias
import matplotlib.pyplot as plt

# Complex import patterns
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score


class SampleAPI:
    """Sample API class using various dependencies"""
    
    def __init__(self):
        self.app = FastAPI()
        self.logger = logging.getLogger(__name__)
        
    def process_data(self, data: List[Dict]) -> pd.DataFrame:
        """Process data using pandas and numpy"""
        df = pd.DataFrame(data)
        return df.fillna(0)
    
    def make_request(self, url: str) -> Dict:
        """Make HTTP request using requests library"""
        response = requests.get(url)
        return response.json()
    
    def generate_plot(self, data: np.ndarray) -> str:
        """Generate plot using matplotlib"""
        plt.figure(figsize=(10, 6))
        plt.plot(data)
        plt.savefig("output.png")
        return "output.png"


if __name__ == "__main__":
    # This would normally import uvicorn for running the app
    # import uvicorn
    pass