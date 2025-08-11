"""
Utility functions for the dependency reader
"""

import logging
import sys
from typing import List, Dict, Any
from pathlib import Path

import colorlog

from .models import DependencyFile, Dependency, ConflictReport


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Create colored formatter
    formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s: %(message)s',
        datefmt=None,
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={},
        style='%'
    )
    
    # Setup handler
    handler = colorlog.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(handler)


def format_dependencies(dependencies: List[Dependency], format_type: str = "table") -> str:
    """Format dependencies for display"""
    if not dependencies:
        return "No dependencies found"
    
    if format_type == "json":
        import json
        data = []
        for dep in dependencies:
            data.append({
                'name': dep.name,
                'version_spec': str(dep.version_spec) if dep.version_spec else None,
                'extras': dep.extras,
                'is_dev': dep.is_dev
            })
        return json.dumps(data, indent=2)
    
    elif format_type == "table":
        # Group by dev/prod
        prod_deps = [d for d in dependencies if not d.is_dev]
        dev_deps = [d for d in dependencies if d.is_dev]
        
        result = []
        
        if prod_deps:
            result.append("Production Dependencies:")
            for dep in sorted(prod_deps, key=lambda x: x.name.lower()):
                version_str = f" {dep.version_spec}" if dep.version_spec else ""
                extras_str = f"[{','.join(dep.extras)}]" if dep.extras else ""
                result.append(f"  • {dep.name}{extras_str}{version_str}")
        
        if dev_deps:
            if result:
                result.append("")
            result.append("Development Dependencies:")
            for dep in sorted(dev_deps, key=lambda x: x.name.lower()):
                version_str = f" {dep.version_spec}" if dep.version_spec else ""
                extras_str = f"[{','.join(dep.extras)}]" if dep.extras else ""
                result.append(f"  • {dep.name}{extras_str}{version_str}")
        
        return "\n".join(result)
    
    else:  # simple format
        result = []
        for dep in sorted(dependencies, key=lambda x: x.name.lower()):
            result.append(str(dep))
        return "\n".join(result)


def format_conflicts(conflicts: List[ConflictReport], format_type: str = "table") -> str:
    """Format conflicts for display"""
    if not conflicts:
        return "No conflicts found"
    
    if format_type == "json":
        import json
        data = []
        for conflict in conflicts:
            data.append({
                'package': conflict.package_name,
                'conflicts': [
                    {
                        'file': str(vc.file_path),
                        'file_type': vc.file_type,
                        'version_spec': str(vc.version_spec) if vc.version_spec else None,
                        'is_dev': vc.is_dev
                    }
                    for vc in conflict.version_conflicts
                ]
            })
        return json.dumps(data, indent=2)
    
    else:  # table or simple format
        result = []
        for conflict in conflicts:
            result.append(f"• {conflict.package_name}:")
            for version_conflict in conflict.version_conflicts:
                version_str = str(version_conflict.version_spec) if version_conflict.version_spec else "any version"
                dev_str = " [DEV]" if version_conflict.is_dev else ""
                result.append(f"    {version_conflict.file_path}: {version_str}{dev_str}")
            result.append("")  # Empty line between conflicts
        
        return "\n".join(result)


def validate_dependency_file(file_path: Path) -> bool:
    """Validate that a file exists and is readable"""
    if not file_path.exists():
        return False
    
    if not file_path.is_file():
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read(1)  # Try to read at least one character
        return True
    except (OSError, UnicodeDecodeError):
        return False


def normalize_package_name(name: str) -> str:
    """Normalize package name according to PEP 508"""
    # Convert to lowercase and replace underscores/hyphens
    import re
    return re.sub(r'[-_.]+', '-', name.lower())


def compare_versions(version1: str, version2: str) -> int:
    """Compare two version strings"""
    try:
        from packaging.version import Version
        v1 = Version(version1)
        v2 = Version(version2)
        
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0
    except Exception:
        # Fallback to string comparison
        if version1 < version2:
            return -1
        elif version1 > version2:
            return 1
        else:
            return 0


def get_file_type_from_path(file_path: Path) -> str:
    """Determine file type from file path"""
    filename = file_path.name.lower()
    
    if filename == "requirements.txt":
        return "requirements.txt"
    elif filename == "pipfile":
        return "Pipfile"
    elif filename == "pyproject.toml":
        return "pyproject.toml"
    elif filename.endswith(".txt") and "requirement" in filename:
        return "requirements.txt"
    else:
        return "unknown"


def merge_dependencies(deps1: List[Dependency], deps2: List[Dependency]) -> List[Dependency]:
    """Merge two lists of dependencies, handling duplicates"""
    merged = {}
    
    # Add all dependencies from first list
    for dep in deps1:
        key = (dep.name.lower(), dep.is_dev)
        merged[key] = dep
    
    # Add dependencies from second list, updating if newer or more specific
    for dep in deps2:
        key = (dep.name.lower(), dep.is_dev)
        if key not in merged:
            merged[key] = dep
        else:
            # Keep the more specific version if possible
            existing = merged[key]
            if existing.version_spec is None and dep.version_spec is not None:
                merged[key] = dep
            elif dep.extras and not existing.extras:
                merged[key] = dep
    
    return list(merged.values())


def create_summary_report(dependency_files: List[DependencyFile], conflicts: List[ConflictReport]) -> Dict[str, Any]:
    """Create a summary report of all parsed information"""
    total_deps = sum(len(df.dependencies) for df in dependency_files)
    total_prod_deps = sum(len(df.get_production_dependencies()) for df in dependency_files)
    total_dev_deps = sum(len(df.get_dev_dependencies()) for df in dependency_files)
    
    # Find unique packages across all files
    all_packages = set()
    for df in dependency_files:
        all_packages.update(df.get_dependency_names())
    
    return {
        'total_files': len(dependency_files),
        'file_types': [df.file_type for df in dependency_files],
        'total_dependencies': total_deps,
        'production_dependencies': total_prod_deps,
        'development_dependencies': total_dev_deps,
        'unique_packages': len(all_packages),
        'conflicts_found': len(conflicts),
        'conflicted_packages': [c.package_name for c in conflicts]
    }
