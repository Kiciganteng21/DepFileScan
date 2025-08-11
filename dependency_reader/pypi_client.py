"""
PyPI client for fetching package information
"""

import time
import logging
import json
from typing import Optional, Dict, Any
from pathlib import Path
import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class PyPIClient:
    """Client for interacting with PyPI API"""
    
    def __init__(self, cache_dir: Optional[Path] = None, rate_limit_delay: float = 0.1):
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://pypi.org/pypi"
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        
        # Setup cache directory
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "dependency-reader"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup HTTP session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set user agent
        self.session.headers.update({
            'User-Agent': 'dependency-reader/1.0.0 (Python CLI tool)'
        })
    
    def get_package_info(self, package_name: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get package information from PyPI"""
        
        # Check cache first
        if use_cache:
            cached_info = self._get_cached_info(package_name)
            if cached_info:
                self.logger.debug(f"Using cached info for {package_name}")
                return cached_info
        
        # Rate limiting
        self._enforce_rate_limit()
        
        try:
            url = f"{self.base_url}/{package_name}/json"
            self.logger.debug(f"Fetching package info from: {url}")
            
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 404:
                self.logger.warning(f"Package '{package_name}' not found on PyPI")
                return None
            
            response.raise_for_status()
            package_info = response.json()
            
            # Cache the response
            if use_cache:
                self._cache_info(package_name, package_info)
            
            return package_info
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching package info for '{package_name}': {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing JSON response for '{package_name}': {e}")
            return None
    
    def get_package_versions(self, package_name: str) -> Optional[list]:
        """Get all available versions for a package"""
        package_info = self.get_package_info(package_name)
        
        if not package_info:
            return None
        
        releases = package_info.get('releases', {})
        versions = list(releases.keys())
        
        # Sort versions (basic sorting, could be improved with packaging.version)
        try:
            from packaging.version import Version
            versions.sort(key=lambda v: Version(v), reverse=True)
        except Exception:
            # Fallback to simple string sorting
            versions.sort(reverse=True)
        
        return versions
    
    def get_latest_version(self, package_name: str) -> Optional[str]:
        """Get the latest version of a package"""
        package_info = self.get_package_info(package_name)
        
        if not package_info:
            return None
        
        return package_info.get('info', {}).get('version')
    
    def check_package_exists(self, package_name: str) -> bool:
        """Check if a package exists on PyPI"""
        return self.get_package_info(package_name) is not None
    
    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _get_cache_file_path(self, package_name: str) -> Path:
        """Get the cache file path for a package"""
        # Use a safe filename
        safe_name = "".join(c if c.isalnum() or c in '-_.' else '_' for c in package_name.lower())
        return self.cache_dir / f"{safe_name}.json"
    
    def _get_cached_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Get cached package information"""
        cache_file = self._get_cache_file_path(package_name)
        
        if not cache_file.exists():
            return None
        
        try:
            # Check if cache is still fresh (24 hours)
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age > 86400:  # 24 hours in seconds
                self.logger.debug(f"Cache expired for {package_name}")
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        except Exception as e:
            self.logger.debug(f"Error reading cache for {package_name}: {e}")
            return None
    
    def _cache_info(self, package_name: str, package_info: Dict[str, Any]) -> None:
        """Cache package information"""
        cache_file = self._get_cache_file_path(package_name)
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(package_info, f, indent=2)
            self.logger.debug(f"Cached info for {package_name}")
        
        except Exception as e:
            self.logger.debug(f"Error caching info for {package_name}: {e}")
    
    def clear_cache(self) -> None:
        """Clear all cached package information"""
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            self.logger.info("Cache cleared")
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
