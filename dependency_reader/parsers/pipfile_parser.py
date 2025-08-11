"""
Parser for Pipfile files
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from packaging.specifiers import SpecifierSet

from ..models import DependencyFile, Dependency


class PipfileParser:
    """Parser for Pipfile files"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse(self, file_path: Path) -> DependencyFile:
        """Parse a Pipfile"""
        self.logger.debug(f"Parsing Pipfile: {file_path}")
        
        try:
            # Try to import pipfile library
            try:
                import pipfile
                pf = pipfile.load(str(file_path))
                pipfile_data = pf.data
                self.logger.debug(f"Using pipfile library, parsed sections: {list(pipfile_data.keys())}")
            except ImportError:
                self.logger.warning("pipfile library not available, using manual parsing")
                pipfile_data = self._manual_parse_pipfile(file_path)
                self.logger.debug(f"Manual parsing, parsed sections: {list(pipfile_data.keys())}")
            
            dependencies: List[Dependency] = []
            
            # Parse production dependencies
            packages = pipfile_data.get('default', {}) if pipfile_data else {}
            for package_name, package_spec in packages.items():
                dependency = self._parse_package_spec(package_name, package_spec, is_dev=False)
                if dependency:
                    dependencies.append(dependency)
            
            # Parse development dependencies
            dev_packages = pipfile_data.get('develop', {}) if pipfile_data else {}
            for package_name, package_spec in dev_packages.items():
                dependency = self._parse_package_spec(package_name, package_spec, is_dev=True)
                if dependency:
                    dependencies.append(dependency)
            
            self.logger.info(f"Parsed {len(dependencies)} dependencies from {file_path}")
            
            return DependencyFile(
                file_path=file_path,
                file_type="Pipfile",
                dependencies=dependencies
            )
        
        except Exception as e:
            self.logger.error(f"Error parsing Pipfile {file_path}: {e}")
            raise
    
    def _manual_parse_pipfile(self, file_path: Path) -> Dict[str, Any]:
        """Manually parse Pipfile using TOML parser"""
        try:
            import toml
            with open(file_path, 'r', encoding='utf-8') as f:
                pipfile_data = toml.load(f)
            
            # Convert TOML section names to pipfile library format
            converted_data = {}
            if 'packages' in pipfile_data:
                converted_data['default'] = pipfile_data['packages']
            if 'dev-packages' in pipfile_data:
                converted_data['develop'] = pipfile_data['dev-packages']
            
            return converted_data
        except ImportError:
            self.logger.error("Neither pipfile nor toml library available for parsing Pipfile")
            raise
        except Exception as e:
            self.logger.error(f"Error parsing Pipfile manually: {e}")
            raise
    
    def _parse_package_spec(self, package_name: str, package_spec: Any, is_dev: bool) -> Optional[Dependency]:
        """Parse a package specification from Pipfile"""
        try:
            if isinstance(package_spec, str):
                # Simple version string like ">=1.0.0"
                version_spec = self._parse_version_string(package_spec)
                return Dependency(
                    name=package_name,
                    version_spec=version_spec,
                    extras=[],
                    is_dev=is_dev
                )
            
            elif isinstance(package_spec, dict):
                # Complex specification with version, extras, etc.
                version = package_spec.get('version', '*')
                extras = package_spec.get('extras', [])
                
                # Handle git/URL specifications
                if 'git' in package_spec or 'path' in package_spec or 'file' in package_spec:
                    return Dependency(
                        name=package_name,
                        version_spec=None,  # Git/path deps don't have version specs
                        extras=extras if isinstance(extras, list) else [],
                        is_dev=is_dev
                    )
                
                version_spec = self._parse_version_string(version)
                return Dependency(
                    name=package_name,
                    version_spec=version_spec,
                    extras=extras if isinstance(extras, list) else [],
                    is_dev=is_dev
                )
            
            else:
                self.logger.warning(f"Unknown package spec format for {package_name}: {package_spec}")
                return None
        
        except Exception as e:
            self.logger.warning(f"Error parsing package spec for {package_name}: {e}")
            return None
    
    def _parse_version_string(self, version_str: str) -> Optional[SpecifierSet]:
        """Parse a version string into a SpecifierSet"""
        if not version_str or version_str == '*':
            return None
        
        try:
            # Clean up the version string
            version_str = version_str.strip()
            
            # Handle some common Pipfile version formats
            if version_str.startswith('=='):
                # Already in correct format
                pass
            elif version_str.startswith('~='):
                # Compatible release (already correct)
                pass
            elif version_str.startswith('>='):
                # Greater than or equal (already correct)
                pass
            elif version_str.startswith('>'):
                # Greater than (already correct)
                pass
            elif version_str.startswith('<='):
                # Less than or equal (already correct)
                pass
            elif version_str.startswith('<'):
                # Less than (already correct)
                pass
            elif version_str.startswith('!='):
                # Not equal (already correct)
                pass
            elif version_str.replace('.', '').isdigit():
                # Plain version number, add ==
                version_str = f"=={version_str}"
            
            return SpecifierSet(version_str)
        
        except Exception as e:
            self.logger.warning(f"Could not parse version string '{version_str}': {e}")
            return None
