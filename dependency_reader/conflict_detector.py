"""
Conflict detection for dependencies across different file formats
"""

import logging
from typing import List, Dict, Set, Optional
from collections import defaultdict
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .models import DependencyFile, Dependency, ConflictReport, VersionConflict


class ConflictDetector:
    """Detects conflicts between dependencies across different files"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def detect_conflicts(self, dependency_files: List[DependencyFile]) -> List[ConflictReport]:
        """Detect conflicts between dependency files"""
        self.logger.debug(f"Detecting conflicts across {len(dependency_files)} files")
        
        # Group dependencies by package name
        package_versions: Dict[str, List[VersionConflict]] = defaultdict(list)
        
        for dep_file in dependency_files:
            for dependency in dep_file.dependencies:
                version_conflict = VersionConflict(
                    file_path=dep_file.file_path,
                    file_type=dep_file.file_type,
                    version_spec=dependency.version_spec,
                    is_dev=dependency.is_dev
                )
                package_versions[dependency.name].append(version_conflict)
        
        # Find conflicts
        conflicts: List[ConflictReport] = []
        
        for package_name, version_conflicts in package_versions.items():
            if len(version_conflicts) > 1:
                conflict = self._analyze_version_conflicts(package_name, version_conflicts)
                if conflict:
                    conflicts.append(conflict)
        
        self.logger.info(f"Found {len(conflicts)} package conflicts")
        return conflicts
    
    def _analyze_version_conflicts(self, package_name: str, version_conflicts: List[VersionConflict]) -> Optional[ConflictReport]:
        """Analyze version conflicts for a specific package"""
        
        # Check if there are actual conflicts
        has_conflicts = False
        
        # Group by dev/prod
        prod_specs: List[SpecifierSet] = []
        dev_specs: List[SpecifierSet] = []
        
        for version_conflict in version_conflicts:
            if version_conflict.version_spec:
                if version_conflict.is_dev:
                    dev_specs.append(version_conflict.version_spec)
                else:
                    prod_specs.append(version_conflict.version_spec)
        
        # Check for conflicts within production dependencies
        if len(prod_specs) > 1:
            if not self._are_compatible_specs(prod_specs):
                has_conflicts = True
        
        # Check for conflicts within dev dependencies
        if len(dev_specs) > 1:
            if not self._are_compatible_specs(dev_specs):
                has_conflicts = True
        
        # Check for conflicts between prod and dev (optional check)
        # This might be too strict as dev deps can have different versions
        if prod_specs and dev_specs:
            # Only report if there's a clear incompatibility
            all_specs = prod_specs + dev_specs
            if not self._are_compatible_specs(all_specs):
                # Only flag as conflict if it's severe
                if self._has_severe_conflicts(all_specs):
                    has_conflicts = True
        
        # Check for different specification formats that might conflict
        has_different_specs = self._has_different_specification_formats(version_conflicts)
        
        if has_conflicts or has_different_specs:
            return ConflictReport(
                package_name=package_name,
                version_conflicts=version_conflicts
            )
        
        return None
    
    def _are_compatible_specs(self, specs: List[SpecifierSet]) -> bool:
        """Check if version specifiers are compatible"""
        if len(specs) <= 1:
            return True
        
        try:
            # Try to find a version that satisfies all specs
            # This is a simplified check - we'll use a common approach
            
            # Collect all individual specifiers
            all_specifiers = []
            for spec_set in specs:
                all_specifiers.extend(spec_set)
            
            # Check for obvious conflicts
            exact_versions = set()
            for spec in all_specifiers:
                if spec.operator == '==':
                    exact_versions.add(spec.version)
            
            # If we have multiple exact versions, that's a conflict
            if len(exact_versions) > 1:
                return False
            
            # Check for impossible combinations
            min_versions = []
            max_versions = []
            
            for spec in all_specifiers:
                if spec.operator in ['>=', '>']:
                    min_versions.append(Version(spec.version))
                elif spec.operator in ['<=', '<']:
                    max_versions.append(Version(spec.version))
                elif spec.operator == '!=':
                    # Exclusions are harder to check, skip for now
                    pass
            
            if min_versions and max_versions:
                max_min = max(min_versions)
                min_max = min(max_versions)
                if max_min > min_max:
                    return False
            
            return True
        
        except Exception as e:
            self.logger.debug(f"Error checking spec compatibility: {e}")
            # If we can't determine, assume no conflict
            return True
    
    def _has_severe_conflicts(self, specs: List[SpecifierSet]) -> bool:
        """Check if there are severe conflicts (different major versions, etc.)"""
        try:
            exact_versions = []
            for spec_set in specs:
                for spec in spec_set:
                    if spec.operator == '==':
                        exact_versions.append(Version(spec.version))
            
            if len(exact_versions) >= 2:
                # Check for different major versions
                major_versions = set(v.major for v in exact_versions)
                if len(major_versions) > 1:
                    return True
            
            return False
        
        except Exception:
            return False
    
    def _has_different_specification_formats(self, version_conflicts: List[VersionConflict]) -> bool:
        """Check if different files specify versions in conflicting ways"""
        
        # Check for None vs specified versions
        has_version_spec = any(vc.version_spec is not None for vc in version_conflicts)
        has_no_version_spec = any(vc.version_spec is None for vc in version_conflicts)
        
        # If some files specify versions and others don't, it might be worth noting
        # but it's not necessarily a conflict
        if has_version_spec and has_no_version_spec:
            # Only report as conflict if multiple files have different specific versions
            specific_specs = [vc for vc in version_conflicts if vc.version_spec is not None]
            if len(specific_specs) > 1:
                valid_specs = [vc.version_spec for vc in specific_specs if vc.version_spec is not None]
                return not self._are_compatible_specs(valid_specs)
        
        return False
