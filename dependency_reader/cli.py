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
@click.argument('package_name')
@click.option('--format', '-f', type=click.Choice(['json', 'simple']), 
              default='simple', help='Output format')
def info(package_name: str, format: str) -> None:
    """Get information about a package from PyPI"""
    logger = logging.getLogger(__name__)
    
    try:
        pypi_client = PyPIClient()
        package_info = pypi_client.get_package_info(package_name)
        
        if not package_info:
            logger.error(f"Package '{package_name}' not found on PyPI")
            return
        
        if format == 'json':
            import json
            click.echo(json.dumps(package_info, indent=2))
        else:
            info_data = package_info.get('info', {})
            click.echo(f"Package: {info_data.get('name', 'Unknown')}")
            click.echo(f"Version: {info_data.get('version', 'Unknown')}")
            click.echo(f"Summary: {info_data.get('summary', 'No summary available')}")
            click.echo(f"Author: {info_data.get('author', 'Unknown')}")
            click.echo(f"License: {info_data.get('license', 'Unknown')}")
            
            requires_dist = info_data.get('requires_dist', [])
            if requires_dist:
                click.echo(f"Dependencies: {', '.join(requires_dist[:5])}")
                if len(requires_dist) > 5:
                    click.echo(f"  ... and {len(requires_dist) - 5} more")
    
    except Exception as e:
        logger.error(f"Error fetching package information: {e}")


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
