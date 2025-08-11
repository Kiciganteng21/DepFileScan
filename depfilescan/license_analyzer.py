
"""
License compatibility analysis for dependencies
"""

import logging
from typing import List, Dict, Set
from collections import defaultdict

from .models import PackageInfo, LicenseInfo
from .utils import get_license_info


class LicenseAnalyzer:
    """Analyze license compatibility across dependencies"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # License compatibility matrix
        self.compatibility_matrix = {
            "permissive": {"permissive", "weak_copyleft", "strong_copyleft", "proprietary"},
            "weak_copyleft": {"permissive", "weak_copyleft"},
            "strong_copyleft": {"permissive", "strong_copyleft"},
            "proprietary": {"permissive"},
            "unknown": set()  # Unknown licenses are incompatible with everything
        }
    
    def analyze_licenses(self, package_infos: List[PackageInfo]) -> Dict[str, any]:
        """Analyze license compatibility across all packages"""
        license_groups = defaultdict(list)
        compatibility_issues = []
        commercial_issues = []
        
        # Group packages by license compatibility level
        for package_info in package_infos:
            license_info = get_license_info(package_info.license)
            package_info.license_info = license_info
            
            license_groups[license_info.compatibility_level].append(package_info)
            
            # Check for commercial friendliness issues
            if not license_info.is_commercial_friendly:
                commercial_issues.append(package_info)
        
        # Check for compatibility issues
        compatibility_issues = self._find_compatibility_issues(license_groups)
        
        return {
            "license_groups": dict(license_groups),
            "compatibility_issues": compatibility_issues,
            "commercial_issues": commercial_issues,
            "summary": self._generate_license_summary(license_groups)
        }
    
    def _find_compatibility_issues(self, license_groups: Dict[str, List[PackageInfo]]) -> List[str]:
        """Find potential license compatibility issues"""
        issues = []
        
        # Check if we have strong copyleft with proprietary
        if license_groups.get("strong_copyleft") and license_groups.get("proprietary"):
            issues.append(
                "Strong copyleft licenses (GPL) are incompatible with proprietary licenses"
            )
        
        # Check for unknown licenses
        if license_groups.get("unknown"):
            unknown_packages = [pkg.name for pkg in license_groups["unknown"]]
            issues.append(
                f"Unknown licenses detected in: {', '.join(unknown_packages)}. "
                "Manual review required."
            )
        
        # Warn about mixing copyleft with commercial code
        if (license_groups.get("strong_copyleft") or license_groups.get("weak_copyleft")):
            if license_groups.get("proprietary"):
                issues.append(
                    "Mixing copyleft and proprietary licenses may require legal review"
                )
        
        return issues
    
    def _generate_license_summary(self, license_groups: Dict[str, List[PackageInfo]]) -> Dict[str, int]:
        """Generate a summary of license distribution"""
        return {
            "permissive": len(license_groups.get("permissive", [])),
            "weak_copyleft": len(license_groups.get("weak_copyleft", [])),
            "strong_copyleft": len(license_groups.get("strong_copyleft", [])),
            "proprietary": len(license_groups.get("proprietary", [])),
            "unknown": len(license_groups.get("unknown", []))
        }
    
    def get_license_recommendations(self, license_analysis: Dict) -> List[str]:
        """Get recommendations based on license analysis"""
        recommendations = []
        
        if license_analysis["commercial_issues"]:
            recommendations.append(
                "Consider replacing packages with non-commercial-friendly licenses if "
                "building a commercial product"
            )
        
        if license_analysis["compatibility_issues"]:
            recommendations.append(
                "Review license compatibility issues and consider alternative packages"
            )
        
        unknown_count = license_analysis["summary"]["unknown"]
        if unknown_count > 0:
            recommendations.append(
                f"Review {unknown_count} packages with unknown licenses manually"
            )
        
        if not recommendations:
            recommendations.append("No license compatibility issues detected")
        
        return recommendations
</pathlib>
