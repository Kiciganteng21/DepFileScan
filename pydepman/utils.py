"""
Utility functions for the dependency reader
"""

import csv
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import colorlog
from packaging.specifiers import SpecifierSet

from .models import Dependency, DependencyFile, ConflictReport, ProjectReport, LicenseInfo


def setup_logging(verbose: bool = False, log_file: Optional[Path] = None) -> None:
    """Setup logging configuration"""
    log_level = logging.DEBUG if verbose else logging.INFO

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Setup console handler with color
    console_handler = colorlog.StreamHandler()
    console_handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)-8s%(reset)s %(blue)s%(name)s%(reset)s: %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    ))

    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(console_handler)

    # Add file handler if log file specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def format_dependencies(dependencies: List[Dependency], format_type: str = "simple") -> str:
    """Format dependencies for display"""
    if format_type == "json":
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
        # Enhanced table format with Unicode box drawing
        lines = ["┌─────────────────────┬─────────────────┬──────────┬──────────┐"]
        lines.append("│ Package             │ Version         │ Type     │ Extras   │")
        lines.append("├─────────────────────┼─────────────────┼──────────┼──────────┤")

        for dep in dependencies:
            name = dep.name[:19].ljust(19)
            version_str = (str(dep.version_spec) if dep.version_spec else "any")[:15].ljust(15)
            dep_type = ("dev" if dep.is_dev else "prod").ljust(8)
            extras = ",".join(dep.extras)[:8].ljust(8)
            lines.append(f"│ {name} │ {version_str} │ {dep_type} │ {extras} │")

        lines.append("└─────────────────────┴─────────────────┴──────────┴──────────┘")
        return "\n".join(lines)

    else:  # simple format
        lines = []
        for dep in dependencies:
            version_str = f" {dep.version_spec}" if dep.version_spec else ""
            dev_str = " [DEV]" if dep.is_dev else ""
            extras_str = f"[{','.join(dep.extras)}]" if dep.extras else ""
            lines.append(f"{dep.name}{extras_str}{version_str}{dev_str}")
        return "\n".join(lines)


def format_conflicts(conflicts: List[ConflictReport], format_type: str = "simple") -> str:
    """Format conflicts for display"""
    if format_type == "json":
        data = []
        for conflict in conflicts:
            data.append({
                'package': conflict.package_name,
                'conflicts': [
                    {
                        'file': str(vc.file_path),
                        'version_spec': str(vc.version_spec) if vc.version_spec else None,
                        'is_dev': vc.is_dev
                    }
                    for vc in conflict.version_conflicts
                ]
            })
        return json.dumps(data, indent=2)

    else:
        lines = []
        for conflict in conflicts:
            lines.append(f"⚠️  Conflict for {conflict.package_name}:")
            for vc in conflict.version_conflicts:
                version_str = str(vc.version_spec) if vc.version_spec else "any version"
                dev_str = " [DEV]" if vc.is_dev else ""
                lines.append(f"   📄 {vc.file_path}: {version_str}{dev_str}")
            lines.append("")  # Empty line between conflicts
        return "\n".join(lines)


def generate_html_report(report: ProjectReport, output_path: Path) -> None:
    """Generate comprehensive HTML report"""
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Dependency Analysis Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .vulnerability {{ background: #ffebee; padding: 10px; margin: 5px 0; border-left: 4px solid #f44336; }}
        .conflict {{ background: #fff3e0; padding: 10px; margin: 5px 0; border-left: 4px solid #ff9800; }}
        .stats {{ display: flex; gap: 20px; }}
        .stat-box {{ background: #e3f2fd; padding: 15px; border-radius: 5px; text-align: center; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Dependency Analysis Report</h1>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="section">
        <h2>📈 Summary</h2>
        <div class="stats">
            <div class="stat-box">
                <h3>{report.total_packages}</h3>
                <p>Total Packages</p>
            </div>
            <div class="stat-box">
                <h3>{report.unique_packages}</h3>
                <p>Unique Packages</p>
            </div>
            <div class="stat-box">
                <h3>{len(report.conflicts)}</h3>
                <p>Conflicts</p>
            </div>
            <div class="stat-box">
                <h3>{len(report.vulnerabilities)}</h3>
                <p>Vulnerabilities</p>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>🔍 Dependency Files</h2>
        <table>
            <tr><th>File</th><th>Type</th><th>Dependencies</th></tr>
            {''.join(f'<tr><td>{df.file_path}</td><td>{df.file_type}</td><td>{len(df.dependencies)}</td></tr>' for df in report.dependency_files)}
        </table>
    </div>

    {'<div class="section"><h2>⚠️ Conflicts</h2>' + ''.join(f'<div class="conflict"><strong>{c.package_name}</strong><br>' + '<br>'.join(f'{vc.file_path}: {vc.version_spec}' for vc in c.version_conflicts) + '</div>' for c in report.conflicts) + '</div>' if report.conflicts else ''}

    {'<div class="section"><h2>🛡️ Vulnerabilities</h2>' + ''.join(f'<div class="vulnerability"><strong>{v.package_name}</strong> - {v.severity}<br>{v.description}</div>' for v in report.vulnerabilities) + '</div>' if report.vulnerabilities else ''}

</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


def export_to_csv(dependencies: List[Dependency], output_path: Path) -> None:
    """Export dependencies to CSV format"""
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Package', 'Version', 'Type', 'Extras'])

        for dep in dependencies:
            writer.writerow([
                dep.name,
                str(dep.version_spec) if dep.version_spec else '',
                'dev' if dep.is_dev else 'prod',
                ','.join(dep.extras)
            ])


def normalize_package_name(name: str) -> str:
    """Normalize package name following PEP 508"""
    import re
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_version_spec(version_string: str) -> Optional[SpecifierSet]:
    """Parse version specification string"""
    if not version_string or version_string == "*":
        return None

    try:
        return SpecifierSet(version_string)
    except Exception:
        return None


def validate_version_compatibility(spec1: SpecifierSet, spec2: SpecifierSet) -> bool:
    """Check if two version specifications are compatible"""
    if not spec1 or not spec2:
        return True

    # For now, simple check - in practice would need more sophisticated logic
    return str(spec1) == str(spec2)


def get_license_info(license_string: str) -> LicenseInfo:
    """Get license compatibility information"""
    license_lower = license_string.lower() if license_string else ""

    # Common permissive licenses
    if any(lic in license_lower for lic in ['mit', 'bsd', 'apache', 'isc']):
        return LicenseInfo(
            license_name=license_string,
            is_commercial_friendly=True,
            is_copyleft=False,
            compatibility_level="permissive"
        )

    # Weak copyleft
    if any(lic in license_lower for lic in ['lgpl', 'mpl']):
        return LicenseInfo(
            license_name=license_string,
            is_commercial_friendly=True,
            is_copyleft=True,
            compatibility_level="weak_copyleft"
        )

    # Strong copyleft
    if any(lic in license_lower for lic in ['gpl', 'agpl']):
        return LicenseInfo(
            license_name=license_string,
            is_commercial_friendly=False,
            is_copyleft=True,
            compatibility_level="strong_copyleft"
        )

    # Default unknown
    return LicenseInfo(
        license_name=license_string or "Unknown",
        is_commercial_friendly=False,
        is_copyleft=False,
        compatibility_level="unknown"
    )


def suggest_conflict_resolution(conflict: ConflictReport) -> List[str]:
    """Suggest resolution strategies for conflicts"""
    suggestions = []

    if conflict.has_dev_prod_conflicts():
        suggestions.append("Consider moving the package to either production or development dependencies only")

    if conflict.has_version_conflicts():
        # Find the most restrictive version
        version_specs = [vc.version_spec for vc in conflict.version_conflicts if vc.version_spec]
        if version_specs:
            suggestions.append(f"Try using a version that satisfies all constraints: {' and '.join(str(spec) for spec in version_specs)}")

    suggestions.append("Consider using dependency resolution tools like pip-tools or pipenv")

    return suggestions