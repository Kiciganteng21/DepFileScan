
"""
Security vulnerability checking for dependencies
"""

import json
import logging
from typing import List, Dict, Optional
from pathlib import Path

import requests
from packaging.version import Version, InvalidVersion

from .models import SecurityVulnerability, PackageInfo


class SecurityChecker:
    """Check for known security vulnerabilities in dependencies"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.logger = logging.getLogger(__name__)
        self.cache_dir = cache_dir or Path.home() / '.cache' / 'dependency_reader'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        
        # OSV.dev API endpoint for Python packages
        self.osv_api_url = "https://api.osv.dev/v1/query"
    
    def check_package_vulnerabilities(self, package_name: str, version: Optional[str] = None) -> List[SecurityVulnerability]:
        """Check for vulnerabilities in a specific package"""
        try:
            # Query OSV database
            payload = {
                "package": {
                    "name": package_name,
                    "ecosystem": "PyPI"
                }
            }
            
            if version:
                payload["version"] = version
            
            response = self.session.post(
                self.osv_api_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code != 200:
                self.logger.warning(f"Failed to check vulnerabilities for {package_name}: HTTP {response.status_code}")
                return []
            
            data = response.json()
            vulnerabilities = []
            
            for vuln in data.get('vulns', []):
                # Extract vulnerability information
                vuln_id = vuln.get('id', 'Unknown')
                summary = vuln.get('summary', 'No description available')
                
                # Determine severity (simplified)
                severity = self._determine_severity(vuln)
                
                # Get affected versions
                affected_versions = self._extract_affected_versions(vuln)
                
                # Get fixed version
                fixed_version = self._extract_fixed_version(vuln)
                
                vulnerability = SecurityVulnerability(
                    package_name=package_name,
                    affected_versions=affected_versions,
                    vulnerability_id=vuln_id,
                    severity=severity,
                    description=summary,
                    fixed_version=fixed_version
                )
                
                vulnerabilities.append(vulnerability)
            
            return vulnerabilities
            
        except Exception as e:
            self.logger.error(f"Error checking vulnerabilities for {package_name}: {e}")
            return []
    
    def _determine_severity(self, vuln: Dict) -> str:
        """Determine vulnerability severity"""
        # Try to extract severity from database_specific or severity field
        severity = vuln.get('database_specific', {}).get('severity')
        if severity:
            return severity.upper()
        
        # Check for severity in schema
        severity_info = vuln.get('severity', [])
        if severity_info and isinstance(severity_info, list):
            return severity_info[0].get('score', 'MEDIUM').upper()
        
        # Default to medium if not specified
        return 'MEDIUM'
    
    def _extract_affected_versions(self, vuln: Dict) -> str:
        """Extract affected version ranges"""
        affected = vuln.get('affected', [])
        if not affected:
            return "All versions"
        
        ranges = []
        for affect in affected:
            version_ranges = affect.get('ranges', [])
            for version_range in version_ranges:
                events = version_range.get('events', [])
                range_str = self._format_version_range(events)
                if range_str:
                    ranges.append(range_str)
        
        return ', '.join(ranges) if ranges else "Unknown"
    
    def _extract_fixed_version(self, vuln: Dict) -> Optional[str]:
        """Extract the fixed version if available"""
        affected = vuln.get('affected', [])
        for affect in affected:
            version_ranges = affect.get('ranges', [])
            for version_range in version_ranges:
                events = version_range.get('events', [])
                for event in events:
                    if event.get('fixed'):
                        return event['fixed']
        return None
    
    def _format_version_range(self, events: List[Dict]) -> str:
        """Format version range from OSV events"""
        introduced = None
        fixed = None
        
        for event in events:
            if 'introduced' in event:
                introduced = event['introduced']
            elif 'fixed' in event:
                fixed = event['fixed']
        
        if introduced == "0" and fixed:
            return f"< {fixed}"
        elif introduced and fixed:
            return f">= {introduced}, < {fixed}"
        elif introduced:
            return f">= {introduced}"
        else:
            return "Unknown range"
    
    def scan_packages(self, package_infos: List[PackageInfo]) -> List[SecurityVulnerability]:
        """Scan multiple packages for vulnerabilities"""
        all_vulnerabilities = []
        
        for package_info in package_infos:
            self.logger.info(f"Checking vulnerabilities for {package_info.name}...")
            vulns = self.check_package_vulnerabilities(package_info.name, package_info.version)
            all_vulnerabilities.extend(vulns)
        
        return all_vulnerabilities
    
    def is_version_affected(self, vulnerability: SecurityVulnerability, version: str) -> bool:
        """Check if a specific version is affected by a vulnerability"""
        try:
            target_version = Version(version)
            
            # This is a simplified check - in practice would need to parse
            # the affected_versions string properly
            if "All versions" in vulnerability.affected_versions:
                return True
            
            # For now, return True if we can't determine precisely
            return True
            
        except (InvalidVersion, Exception):
            return True  # Err on the side of caution
</pathlib>
