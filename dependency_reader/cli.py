"""
Command Line Interface for the Dependency Reader
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

import click
import colorlog
from packaging.specifiers import SpecifierSet

from .parsers.requirements import RequirementsParser
from .parsers.pipfile_parser import PipfileParser
from .parsers.pyproject_parser import PyprojectParser
from .conflict_detector import ConflictDetector
from .pypi_client import PyPIClient
from .python_scanner import PythonScanner
from .models import DependencyFile, Dependency, ConflictReport
from .utils import setup_logging, format_dependencies, format_conflicts


def setup_colored_logging(verbose: bool = False) -> None:
    """Setup colored logging with colorlog"""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
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
    ))
    
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(handler)


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Python Dependency Reader - Parse and analyze dependency files"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    setup_colored_logging(verbose)


@cli.command()
@click.option('--path', '-p', type=click.Path(exists=True, path_type=Path), 
              default=Path('.'), help='Path to search for dependency files')
@click.option('--recursive', '-r', is_flag=True, help='Search for dependency files recursively in subdirectories')
@click.option('--format', '-f', type=click.Choice(['json', 'table', 'simple']), 
              default='table', help='Output format')
@click.option('--check-pypi', is_flag=True, help='Check PyPI for package information')
@click.option('--detect-conflicts', is_flag=True, help='Detect conflicts between dependency files')
@click.pass_context
def parse(ctx: click.Context, path: Path, recursive: bool, format: str, check_pypi: bool, detect_conflicts: bool) -> None:
    """Parse dependency files in the specified directory"""
    logger = logging.getLogger(__name__)
    
    try:
        # Find dependency files
        dependency_files = find_dependency_files(path, recursive)
        
        if not dependency_files:
            search_type = "recursively" if recursive else "directly"
            logger.warning(f"No dependency files found {search_type} in {path}")
            return
        
        logger.info(f"Found {len(dependency_files)} dependency file(s)")
        
        # Parse all files
        parsed_files: List[DependencyFile] = []
        
        for file_path in dependency_files:
            logger.info(f"Parsing {file_path}")
            parsed_file = parse_dependency_file(file_path)
            if parsed_file:
                parsed_files.append(parsed_file)
        
        if not parsed_files:
            logger.error("No files could be parsed successfully")
            return
        
        # Display parsed dependencies
        display_dependencies(parsed_files, format)
        
        # Check for conflicts if requested
        if detect_conflicts and len(parsed_files) > 1:
            logger.info("Checking for conflicts between dependency files...")
            conflict_detector = ConflictDetector()
            conflicts = conflict_detector.detect_conflicts(parsed_files)
            
            if conflicts:
                click.echo(f"\n\033[31mConflicts detected:\033[0m")
                display_conflicts(conflicts, format)
            else:
                logger.info("No conflicts detected between dependency files")
        
        # Check PyPI if requested
        if check_pypi:
            logger.info("Fetching package information from PyPI...")
            pypi_client = PyPIClient()
            
            for dep_file in parsed_files:
                for dep in dep_file.dependencies:
                    try:
                        package_info = pypi_client.get_package_info(dep.name)
                        if package_info:
                            latest_version = package_info.get('info', {}).get('version', 'Unknown')
                            logger.info(f"{dep.name}: Latest version on PyPI is {latest_version}")
                    except Exception as e:
                        logger.warning(f"Could not fetch PyPI info for {dep.name}: {e}")
    
    except Exception as e:
        logger.error(f"Error parsing dependency files: {e}")
        if ctx.obj.get('verbose'):
            raise


@cli.command()
@click.option('--path', '-p', type=click.Path(exists=True, path_type=Path), 
              default=Path('.'), help='Path to scan for Python files')
@click.option('--recursive', '-r', is_flag=True, help='Scan Python files recursively in subdirectories')
@click.option('--log', '-l', type=str, default='dependencies.txt', help='Log file to save dependencies (default: dependencies.txt)')
@click.option('--format', '-f', type=click.Choice(['json', 'table', 'simple']), 
              default='table', help='Output format')
@click.option('--check-pypi', is_flag=True, help='Check PyPI for package information')
@click.pass_context
def scan(ctx: click.Context, path: Path, recursive: bool, log: str, format: str, check_pypi: bool) -> None:
    """Scan Python files and extract dependencies from import statements"""
    logger = logging.getLogger(__name__)
    
    try:
        scanner = PythonScanner()
        
        if path.is_file():
            # Scan single file
            logger.info(f"Scanning Python file: {path}")
            dependency_file = scanner.scan_file(path)
            dependency_files = [dependency_file] if dependency_file else []
        else:
            # Scan directory
            search_type = "recursively" if recursive else "directly"
            logger.info(f"Scanning {search_type} in directory: {path}")
            dependency_files = scanner.scan_directory(path, recursive)
        
        if not dependency_files:
            logger.warning(f"No Python dependencies found in {path}")
            return
        
        logger.info(f"Found dependencies in {len(dependency_files)} Python file(s)")
        
        # Display dependencies
        display_dependencies(dependency_files, format)
        
        # Save to log file
        log_path = save_dependencies_to_log(dependency_files, log, scanner)
        logger.info(f"Dependencies saved to {log_path}")
        
        # Check PyPI if requested
        if check_pypi:
            logger.info("Fetching package information from PyPI...")
            pypi_client = PyPIClient()
            
            all_packages = set()
            for dep_file in dependency_files:
                for dep in dep_file.dependencies:
                    all_packages.add(dep.name)
            
            for package_name in sorted(all_packages):
                try:
                    package_info = pypi_client.get_package_info(package_name)
                    if package_info:
                        latest_version = package_info.get('info', {}).get('version', 'Unknown')
                        logger.info(f"{package_name}: Latest version on PyPI is {latest_version}")
                    else:
                        logger.warning(f"Package '{package_name}' not found on PyPI (might be a local module)")
                except Exception as e:
                    logger.warning(f"Could not fetch PyPI info for {package_name}: {e}")
    
    except Exception as e:
        logger.error(f"Error scanning Python files: {e}")
        if ctx.obj.get('verbose'):
            raise


@cli.command()
@click.argument('package_name')
@click.option('--format', '-f', type=click.Choice(['json', 'simple']), 
              default='simple', help='Output format')
@click.option('--check-security', is_flag=True, help='Check for security vulnerabilities')
@click.option('--check-license', is_flag=True, help='Analyze license compatibility')
def info(package_name: str, format: str, check_security: bool, check_license: bool) -> None:
    """Get comprehensive information about a package from PyPI"""
    logger = logging.getLogger(__name__)
    
    try:
        pypi_client = PyPIClient()
        package_data = pypi_client.get_package_info(package_name)
        
        if not package_data:
            logger.error(f"Package '{package_name}' not found on PyPI")
            return
        
        package_info = PackageInfo.from_pypi_json(package_data)
        
        if format == 'json':
            data = {
                'name': package_info.name,
                'version': package_info.version,
                'summary': package_info.summary,
                'author': package_info.author,
                'license': package_info.license,
                'homepage': package_info.homepage,
                'requires_python': package_info.requires_python,
                'dependencies': package_info.requires_dist
            }
            
            if check_security:
                from .security_checker import SecurityChecker
                security_checker = SecurityChecker()
                vulnerabilities = security_checker.check_package_vulnerabilities(package_name, package_info.version)
                data['vulnerabilities'] = [
                    {
                        'id': v.vulnerability_id,
                        'severity': v.severity,
                        'description': v.description,
                        'affected_versions': v.affected_versions
                    }
                    for v in vulnerabilities
                ]
            
            if check_license:
                from .license_analyzer import LicenseAnalyzer
                license_analyzer = LicenseAnalyzer()
                license_analysis = license_analyzer.analyze_licenses([package_info])
                data['license_analysis'] = license_analysis
            
            click.echo(json.dumps(data, indent=2))
        else:
            click.echo(f"📦 Package: {package_info.name}")
            click.echo(f"🔖 Version: {package_info.version}")
            click.echo(f"📝 Summary: {package_info.summary or 'No summary available'}")
            click.echo(f"👤 Author: {package_info.author or 'Unknown'}")
            click.echo(f"⚖️  License: {package_info.license or 'Unknown'}")
            click.echo(f"🌐 Homepage: {package_info.homepage or 'Not specified'}")
            click.echo(f"🐍 Python: {package_info.requires_python or 'Any version'}")
            
            if package_info.requires_dist:
                click.echo(f"📋 Dependencies: {', '.join(package_info.requires_dist[:5])}")
                if len(package_info.requires_dist) > 5:
                    click.echo(f"    ... and {len(package_info.requires_dist) - 5} more")
            
            # Security check
            if check_security:
                click.echo(f"\n🛡️  Security Analysis:")
                from .security_checker import SecurityChecker
                security_checker = SecurityChecker()
                vulnerabilities = security_checker.check_package_vulnerabilities(package_name, package_info.version)
                
                if vulnerabilities:
                    click.echo(f"   ⚠️  Found {len(vulnerabilities)} vulnerability(ies):")
                    for vuln in vulnerabilities:
                        click.echo(f"      • {vuln.vulnerability_id} ({vuln.severity}): {vuln.description}")
                else:
                    click.echo("   ✅ No known vulnerabilities found")
            
            # License analysis
            if check_license:
                click.echo(f"\n⚖️  License Analysis:")
                from .license_analyzer import LicenseAnalyzer
                license_analyzer = LicenseAnalyzer()
                license_analysis = license_analyzer.analyze_licenses([package_info])
                
                license_info = package_info.license_info
                if license_info:
                    click.echo(f"   Type: {license_info.compatibility_level}")
                    click.echo(f"   Commercial friendly: {'Yes' if license_info.is_commercial_friendly else 'No'}")
                    click.echo(f"   Copyleft: {'Yes' if license_info.is_copyleft else 'No'}")
    
    except Exception as e:
        logger.error(f"Error fetching package information: {e}")


@cli.command()
@click.option('--path', '-p', type=click.Path(exists=True, path_type=Path), 
              default=Path('.'), help='Path to analyze')
@click.option('--recursive', '-r', is_flag=True, help='Analyze recursively')
@click.option('--output', '-o', type=str, help='Output file for report (HTML/CSV/JSON)')
@click.option('--check-security', is_flag=True, help='Include security vulnerability analysis')
@click.option('--check-licenses', is_flag=True, help='Include license compatibility analysis')
@click.option('--format', '-f', type=click.Choice(['html', 'json', 'csv', 'table']), 
              default='table', help='Report format')
@click.pass_context
def analyze(ctx: click.Context, path: Path, recursive: bool, output: str, 
           check_security: bool, check_licenses: bool, format: str) -> None:
    """Comprehensive dependency analysis with security and license checking"""
    logger = logging.getLogger(__name__)
    
    try:
        from .security_checker import SecurityChecker
        from .license_analyzer import LicenseAnalyzer
        from .utils import generate_html_report, export_to_csv
        
        logger.info("Starting comprehensive dependency analysis...")
        
        # Find and parse dependency files
        dependency_files = find_dependency_files(path, recursive)
        
        if not dependency_files:
            logger.warning("No dependency files found")
            return
        
        parsed_files = []
        for file_path in dependency_files:
            parsed_file = parse_dependency_file(file_path)
            if parsed_file:
                parsed_files.append(parsed_file)
        
        if not parsed_files:
            logger.error("No files could be parsed successfully")
            return
        
        # Detect conflicts
        conflict_detector = ConflictDetector()
        conflicts = conflict_detector.detect_conflicts(parsed_files)
        
        # Collect all packages for analysis
        all_packages = []
        unique_packages = set()
        
        for dep_file in parsed_files:
            for dep in dep_file.dependencies:
                unique_packages.add(dep.name.lower())
        
        # Get PyPI information for unique packages
        pypi_client = PyPIClient()
        package_infos = []
        
        for package_name in unique_packages:
            try:
                package_data = pypi_client.get_package_info(package_name)
                if package_data:
                    package_info = PackageInfo.from_pypi_json(package_data)
                    package_infos.append(package_info)
            except Exception as e:
                logger.warning(f"Could not fetch info for {package_name}: {e}")
        
        # Security analysis
        vulnerabilities = []
        if check_security:
            logger.info("Checking for security vulnerabilities...")
            security_checker = SecurityChecker()
            vulnerabilities = security_checker.scan_packages(package_infos)
        
        # License analysis
        license_analysis = {}
        if check_licenses:
            logger.info("Analyzing license compatibility...")
            license_analyzer = LicenseAnalyzer()
            license_analysis = license_analyzer.analyze_licenses(package_infos)
        
        # Create comprehensive report
        total_deps = sum(len(df.dependencies) for df in parsed_files)
        dev_deps = sum(len([d for d in df.dependencies if d.is_dev]) for df in parsed_files)
        prod_deps = total_deps - dev_deps
        
        report = ProjectReport(
            dependency_files=parsed_files,
            conflicts=conflicts,
            vulnerabilities=vulnerabilities,
            license_issues=license_analysis.get('compatibility_issues', []),
            outdated_packages=[],  # TODO: Implement outdated package detection
            dependency_tree=None,  # TODO: Implement dependency tree
            total_packages=total_deps,
            unique_packages=len(unique_packages),
            dev_packages=dev_deps,
            prod_packages=prod_deps
        )
        
        # Display results
        display_comprehensive_report(report, format)
        
        # Save to file if requested
        if output:
            output_path = Path(output)
            if format == 'html' or output_path.suffix.lower() == '.html':
                generate_html_report(report, output_path)
                logger.info(f"HTML report saved to {output_path}")
            elif format == 'json' or output_path.suffix.lower() == '.json':
                with open(output_path, 'w') as f:
                    json.dump({
                        'summary': {
                            'total_packages': report.total_packages,
                            'unique_packages': report.unique_packages,
                            'conflicts': len(report.conflicts),
                            'vulnerabilities': len(report.vulnerabilities)
                        },
                        'files': [{'path': str(df.file_path), 'type': df.file_type, 'deps': len(df.dependencies)} for df in report.dependency_files],
                        'conflicts': [{'package': c.package_name, 'files': len(c.version_conflicts)} for c in report.conflicts],
                        'vulnerabilities': [{'package': v.package_name, 'severity': v.severity, 'id': v.vulnerability_id} for v in report.vulnerabilities]
                    }, f, indent=2)
                logger.info(f"JSON report saved to {output_path}")
            elif format == 'csv' or output_path.suffix.lower() == '.csv':
                all_deps = []
                for df in report.dependency_files:
                    all_deps.extend(df.dependencies)
                export_to_csv(all_deps, output_path)
                logger.info(f"CSV report saved to {output_path}")
    
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        if ctx.obj.get('verbose'):
            raise


@cli.command()
@click.option('--path', '-p', type=click.Path(exists=True, path_type=Path), 
              default=Path('.'), help='Path to check for vulnerabilities')
@click.option('--recursive', '-r', is_flag=True, help='Check recursively')
@click.option('--severity', type=click.Choice(['low', 'medium', 'high', 'critical']), 
              help='Filter by minimum severity level')
def security(path: Path, recursive: bool, severity: str) -> None:
    """Check dependencies for security vulnerabilities"""
    logger = logging.getLogger(__name__)
    
    try:
        from .security_checker import SecurityChecker
        
        # Find and parse dependency files
        dependency_files = find_dependency_files(path, recursive)
        parsed_files = []
        
        for file_path in dependency_files:
            parsed_file = parse_dependency_file(file_path)
            if parsed_file:
                parsed_files.append(parsed_file)
        
        if not parsed_files:
            logger.warning("No dependency files found to check")
            return
        
        # Collect unique packages
        unique_packages = set()
        for dep_file in parsed_files:
            for dep in dep_file.dependencies:
                unique_packages.add(dep.name.lower())
        
        # Check vulnerabilities
        security_checker = SecurityChecker()
        all_vulnerabilities = []
        
        for package_name in unique_packages:
            vulnerabilities = security_checker.check_package_vulnerabilities(package_name)
            all_vulnerabilities.extend(vulnerabilities)
        
        # Filter by severity if specified
        if severity:
            severity_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
            min_level = severity_order[severity]
            all_vulnerabilities = [
                v for v in all_vulnerabilities 
                if severity_order.get(v.severity.lower(), 1) >= min_level
            ]
        
        # Display results
        if all_vulnerabilities:
            click.echo(f"🛡️  Found {len(all_vulnerabilities)} security vulnerability(ies):\n")
            
            for vuln in all_vulnerabilities:
                severity_color = {
                    'LOW': 'blue',
                    'MEDIUM': 'yellow', 
                    'HIGH': 'magenta',
                    'CRITICAL': 'red'
                }.get(vuln.severity, 'white')
                
                click.echo(f"📦 {vuln.package_name}")
                click.echo(f"   ID: {vuln.vulnerability_id}")
                click.echo(click.style(f"   Severity: {vuln.severity}", fg=severity_color))
                click.echo(f"   Affected: {vuln.affected_versions}")
                click.echo(f"   Description: {vuln.description}")
                if vuln.fixed_version:
                    click.echo(click.style(f"   Fixed in: {vuln.fixed_version}", fg='green'))
                click.echo()
        else:
            click.echo(click.style("✅ No security vulnerabilities found!", fg='green'))
    
    except Exception as e:
        logger.error(f"Error checking security vulnerabilities: {e}")


@cli.command()
@click.option('--path', '-p', type=click.Path(exists=True, path_type=Path), 
              default=Path('.'), help='Path to analyze licenses')
@click.option('--recursive', '-r', is_flag=True, help='Analyze recursively')
@click.option('--commercial', is_flag=True, help='Show only commercial compatibility issues')
def licenses(path: Path, recursive: bool, commercial: bool) -> None:
    """Analyze license compatibility across dependencies"""
    logger = logging.getLogger(__name__)
    
    try:
        from .license_analyzer import LicenseAnalyzer
        
        # Find and parse dependency files
        dependency_files = find_dependency_files(path, recursive)
        parsed_files = []
        
        for file_path in dependency_files:
            parsed_file = parse_dependency_file(file_path)
            if parsed_file:
                parsed_files.append(parsed_file)
        
        if not parsed_files:
            logger.warning("No dependency files found to analyze")
            return
        
        # Get package information
        unique_packages = set()
        for dep_file in parsed_files:
            for dep in dep_file.dependencies:
                unique_packages.add(dep.name.lower())
        
        pypi_client = PyPIClient()
        package_infos = []
        
        for package_name in unique_packages:
            try:
                package_data = pypi_client.get_package_info(package_name)
                if package_data:
                    package_info = PackageInfo.from_pypi_json(package_data)
                    package_infos.append(package_info)
            except Exception as e:
                logger.warning(f"Could not fetch license info for {package_name}: {e}")
        
        # Analyze licenses
        license_analyzer = LicenseAnalyzer()
        license_analysis = license_analyzer.analyze_licenses(package_infos)
        
        # Display results
        click.echo("⚖️  License Analysis Results\n")
        
        # Show summary
        summary = license_analysis['summary']
        click.echo("📊 License Distribution:")
        click.echo(f"   Permissive: {summary['permissive']}")
        click.echo(f"   Weak Copyleft: {summary['weak_copyleft']}")
        click.echo(f"   Strong Copyleft: {summary['strong_copyleft']}")
        click.echo(f"   Proprietary: {summary['proprietary']}")
        click.echo(f"   Unknown: {summary['unknown']}")
        click.echo()
        
        # Show compatibility issues
        if license_analysis['compatibility_issues']:
            click.echo(click.style("⚠️  Compatibility Issues:", fg='yellow'))
            for issue in license_analysis['compatibility_issues']:
                click.echo(f"   • {issue}")
            click.echo()
        
        # Show commercial issues if requested
        if commercial or license_analysis['commercial_issues']:
            click.echo("💼 Commercial Compatibility:")
            if license_analysis['commercial_issues']:
                click.echo(click.style("   ⚠️  Non-commercial-friendly packages:", fg='red'))
                for pkg in license_analysis['commercial_issues']:
                    click.echo(f"      • {pkg.name} ({pkg.license})")
            else:
                click.echo(click.style("   ✅ All packages are commercial-friendly", fg='green'))
            click.echo()
        
        # Show recommendations
        recommendations = license_analyzer.get_license_recommendations(license_analysis)
        click.echo("💡 Recommendations:")
        for rec in recommendations:
            click.echo(f"   • {rec}")
    
    except Exception as e:
        logger.error(f"Error analyzing licenses: {e}")


def find_dependency_files(path: Path, recursive: bool = False) -> List[Path]:
    """Find all dependency files in the given path"""
    dependency_files = []
    
    if recursive:
        # Recursively search for dependency files
        logger = logging.getLogger(__name__)
        logger.debug(f"Searching recursively in {path}")
        
        # Search for requirements.txt files
        for req_file in path.rglob("requirements*.txt"):
            if req_file.is_file() and not req_file.name.startswith('.'):
                dependency_files.append(req_file)
        
        # Search for Pipfiles
        for pipfile in path.rglob("Pipfile"):
            if pipfile.is_file() and not pipfile.name.startswith('.'):
                dependency_files.append(pipfile)
        
        # Search for pyproject.toml files
        for pyproject_file in path.rglob("pyproject.toml"):
            if pyproject_file.is_file() and not pyproject_file.name.startswith('.'):
                dependency_files.append(pyproject_file)
        
        # Filter out files in common ignore directories
        ignore_dirs = {'.git', '.tox', '.venv', 'venv', 'env', '__pycache__', 
                      'node_modules', '.pytest_cache', 'build', 'dist', '.eggs'}
        
        filtered_files = []
        for file_path in dependency_files:
            # Check if any parent directory is in ignore list
            if not any(part.name in ignore_dirs for part in file_path.parents):
                filtered_files.append(file_path)
        
        dependency_files = filtered_files
    else:
        # Only check the specified directory
        # Check for requirements.txt
        req_file = path / "requirements.txt"
        if req_file.exists():
            dependency_files.append(req_file)
        
        # Check for Pipfile
        pipfile = path / "Pipfile"
        if pipfile.exists():
            dependency_files.append(pipfile)
        
        # Check for pyproject.toml
        pyproject_file = path / "pyproject.toml"
        if pyproject_file.exists():
            dependency_files.append(pyproject_file)
    
    return dependency_files


def parse_dependency_file(file_path: Path) -> Optional[DependencyFile]:
    """Parse a dependency file based on its type"""
    logger = logging.getLogger(__name__)
    
    try:
        if file_path.name == "requirements.txt":
            parser = RequirementsParser()
            return parser.parse(file_path)
        elif file_path.name == "Pipfile":
            parser = PipfileParser()
            return parser.parse(file_path)
        elif file_path.name == "pyproject.toml":
            parser = PyprojectParser()
            return parser.parse(file_path)
        else:
            logger.warning(f"Unknown file type: {file_path}")
            return None
    except Exception as e:
        logger.error(f"Error parsing {file_path}: {e}")
        return None


def display_dependencies(dependency_files: List[DependencyFile], format: str) -> None:
    """Display parsed dependencies in the specified format"""
    if format == 'json':
        import json
        data = {}
        for dep_file in dependency_files:
            data[str(dep_file.file_path)] = {
                'type': dep_file.file_type,
                'dependencies': [
                    {
                        'name': dep.name,
                        'version_spec': str(dep.version_spec) if dep.version_spec else None,
                        'is_dev': dep.is_dev,
                        'extras': dep.extras
                    }
                    for dep in dep_file.dependencies
                ]
            }
        click.echo(json.dumps(data, indent=2))
    
    elif format == 'table':
        for dep_file in dependency_files:
            click.echo(f"\n\033[34m=== {dep_file.file_path} ({dep_file.file_type}) ===\033[0m")
            
            if not dep_file.dependencies:
                click.echo("No dependencies found")
                continue
            
            # Group by dev/prod
            prod_deps = [d for d in dep_file.dependencies if not d.is_dev]
            dev_deps = [d for d in dep_file.dependencies if d.is_dev]
            
            if prod_deps:
                click.echo(f"\n\033[32mProduction Dependencies:\033[0m")
                for dep in prod_deps:
                    version_str = f" {dep.version_spec}" if dep.version_spec else ""
                    extras_str = f"[{','.join(dep.extras)}]" if dep.extras else ""
                    click.echo(f"  • {dep.name}{extras_str}{version_str}")
            
            if dev_deps:
                click.echo(f"\n\033[33mDevelopment Dependencies:\033[0m")
                for dep in dev_deps:
                    version_str = f" {dep.version_spec}" if dep.version_spec else ""
                    extras_str = f"[{','.join(dep.extras)}]" if dep.extras else ""
                    click.echo(f"  • {dep.name}{extras_str}{version_str}")
    
    else:  # simple format
        for dep_file in dependency_files:
            click.echo(f"\n{dep_file.file_path} ({dep_file.file_type}):")
            for dep in dep_file.dependencies:
                dev_marker = " [DEV]" if dep.is_dev else ""
                version_str = f" {dep.version_spec}" if dep.version_spec else ""
                click.echo(f"  {dep.name}{version_str}{dev_marker}")


def display_conflicts(conflicts: List[ConflictReport], format: str) -> None:
    """Display conflicts in the specified format"""
    if format == 'json':
        import json
        data = []
        for conflict in conflicts:
            data.append({
                'package': conflict.package_name,
                'conflicts': [
                    {
                        'file': str(version_info.file_path),
                        'version_spec': str(version_info.version_spec) if version_info.version_spec else None,
                        'is_dev': version_info.is_dev
                    }
                    for version_info in conflict.version_conflicts
                ]
            })
        click.echo(json.dumps(data, indent=2))
    else:
        for conflict in conflicts:
            click.echo(f"\n\033[31m• {conflict.package_name}:\033[0m")
            for version_info in conflict.version_conflicts:
                dev_marker = " [DEV]" if version_info.is_dev else ""
                version_str = str(version_info.version_spec) if version_info.version_spec else "any version"
                click.echo(f"    {version_info.file_path}: {version_str}{dev_marker}")


def display_comprehensive_report(report: ProjectReport, format: str) -> None:
    """Display comprehensive project report"""
    if format == 'json':
        data = {
            'summary': {
                'total_packages': report.total_packages,
                'unique_packages': report.unique_packages,
                'dev_packages': report.dev_packages,
                'prod_packages': report.prod_packages,
                'conflicts': len(report.conflicts),
                'vulnerabilities': len(report.vulnerabilities),
                'license_issues': len(report.license_issues)
            },
            'dependency_files': [
                {
                    'path': str(df.file_path),
                    'type': df.file_type,
                    'dependencies': len(df.dependencies)
                }
                for df in report.dependency_files
            ],
            'conflicts': [
                {
                    'package': c.package_name,
                    'files': [str(vc.file_path) for vc in c.version_conflicts]
                }
                for c in report.conflicts
            ],
            'vulnerabilities': [
                {
                    'package': v.package_name,
                    'severity': v.severity,
                    'id': v.vulnerability_id,
                    'description': v.description
                }
                for v in report.vulnerabilities
            ]
        }
        click.echo(json.dumps(data, indent=2))
        return
    
    # Rich text display
    click.echo("🔍 Comprehensive Dependency Analysis Report")
    click.echo("=" * 50)
    
    # Summary section
    click.echo(f"\n📊 Summary:")
    click.echo(f"   Total packages: {report.total_packages}")
    click.echo(f"   Unique packages: {report.unique_packages}")
    click.echo(f"   Production: {report.prod_packages}")
    click.echo(f"   Development: {report.dev_packages}")
    click.echo(f"   Files analyzed: {len(report.dependency_files)}")
    
    # Status indicators
    status_line = "   Status: "
    if report.conflicts:
        status_line += click.style(f"⚠️  {len(report.conflicts)} conflicts ", fg='yellow')
    if report.vulnerabilities:
        status_line += click.style(f"🛡️  {len(report.vulnerabilities)} vulnerabilities ", fg='red')
    if report.license_issues:
        status_line += click.style(f"⚖️  {len(report.license_issues)} license issues ", fg='magenta')
    
    if not (report.conflicts or report.vulnerabilities or report.license_issues):
        status_line += click.style("✅ All clear", fg='green')
    
    click.echo(status_line)
    
    # Dependency files section
    click.echo(f"\n📁 Dependency Files:")
    for df in report.dependency_files:
        click.echo(f"   • {df.file_path} ({df.file_type}) - {len(df.dependencies)} deps")
    
    # Conflicts section
    if report.conflicts:
        click.echo(f"\n⚠️  Version Conflicts:")
        for conflict in report.conflicts:
            click.echo(f"   📦 {conflict.package_name}:")
            for vc in conflict.version_conflicts:
                version_str = str(vc.version_spec) if vc.version_spec else "any"
                dev_str = " [DEV]" if vc.is_dev else ""
                click.echo(f"      • {vc.file_path}: {version_str}{dev_str}")
    
    # Vulnerabilities section
    if report.vulnerabilities:
        click.echo(f"\n🛡️  Security Vulnerabilities:")
        # Group by severity
        by_severity = {}
        for vuln in report.vulnerabilities:
            by_severity.setdefault(vuln.severity, []).append(vuln)
        
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            vulns = by_severity.get(severity, [])
            if vulns:
                color = {'CRITICAL': 'red', 'HIGH': 'magenta', 'MEDIUM': 'yellow', 'LOW': 'blue'}.get(severity, 'white')
                click.echo(click.style(f"   {severity}: {len(vulns)} vulnerability(ies)", fg=color))
                for vuln in vulns[:3]:  # Show first 3
                    click.echo(f"      • {vuln.package_name}: {vuln.vulnerability_id}")
                if len(vulns) > 3:
                    click.echo(f"      ... and {len(vulns) - 3} more")
    
    # License issues section
    if report.license_issues:
        click.echo(f"\n⚖️  License Issues:")
        for issue in report.license_issues:
            click.echo(f"   • {issue}")


def save_dependencies_to_log(dependency_files: List[DependencyFile], log_filename: str, scanner) -> Path:
    """Save dependencies to a log file"""
    from datetime import datetime
    
    log_path = Path(log_filename)
    
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(f"# Python Dependencies Analysis\n")
        f.write(f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Total files analyzed: {len(dependency_files)}\n\n")
        
        # Get package summary
        package_files = scanner.merge_dependencies_by_package(dependency_files)
        
        f.write("## Summary\n")
        f.write(f"Total unique packages found: {len(package_files)}\n\n")
        
        f.write("## Package Usage\n")
        for package_name in sorted(package_files.keys()):
            files = package_files[package_name]
            f.write(f"- {package_name} (used in {len(files)} file(s))\n")
            for file_path in files:
                f.write(f"  - {file_path}\n")
        f.write("\n")
        
        f.write("## Detailed Analysis\n")
        for dep_file in dependency_files:
            f.write(f"\n### {dep_file.file_path}\n")
            if dep_file.dependencies:
                for dep in dep_file.dependencies:
                    f.write(f"- {dep.name}\n")
            else:
                f.write("No external dependencies found\n")
    
    return log_path


def main() -> None:
    """Main entry point for the CLI"""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logging.getLogger(__name__).error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
