"""
Parser for pyproject.toml files (Poetry format)
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from packaging.specifiers import SpecifierSet

from ..models import DependencyFile, Dependency


class PyprojectParser:
    """Parser for pyproject.toml files (Poetry format)"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse(self, file_path: Path) -> DependencyFile:
        """Parse a pyproject.toml file"""
        self.logger.debug(f"Parsing pyproject.toml file: {file_path}")
        
        try:
            import toml
            with open(file_path, 'r', encoding='utf-8') as f:
                pyproject_data = toml.load(f)
        except ImportError:
            self.logger.error("toml library not available for parsing pyproject.toml")
            raise
        except Exception as e:
            self.logger.error(f"Error reading pyproject.toml file {file_path}: {e}")
            raise
        
        dependencies: List[Dependency] = []
        
        # Check if this is a Poetry project
        poetry_section = pyproject_data.get('tool', {}).get('poetry', {})
        if poetry_section:
            dependencies.extend(self._parse_poetry_dependencies(poetry_section))
        
        # Check for PDM project
        pdm_section = pyproject_data.get('project', {})
        if pdm_section:
            dependencies.extend(self._parse_pdm_dependencies(pdm_section))
        
        # Check for Flit project
        flit_section = pyproject_data.get('tool', {}).get('flit', {})
        if flit_section:
            dependencies.extend(self._parse_flit_dependencies(flit_section))
        
        if not dependencies:
            self.logger.warning(f"No recognized dependency format found in {file_path}")
        
        self.logger.info(f"Parsed {len(dependencies)} dependencies from {file_path}")
        
        return DependencyFile(
            file_path=file_path,
            file_type="pyproject.toml",
            dependencies=dependencies
        )
    
    def _parse_poetry_dependencies(self, poetry_section: Dict[str, Any]) -> List[Dependency]:
        """Parse Poetry dependencies from pyproject.toml"""
        dependencies: List[Dependency] = []
        
        # Parse production dependencies
        deps = poetry_section.get('dependencies', {})
        # Remove python dependency as it's not a package dependency
        deps = {k: v for k, v in deps.items() if k.lower() != 'python'}
        
        for package_name, package_spec in deps.items():
            dependency = self._parse_poetry_package_spec(package_name, package_spec, is_dev=False)
            if dependency:
                dependencies.append(dependency)
        
        # Parse development dependencies
        dev_deps = poetry_section.get('dev-dependencies', {})
        for package_name, package_spec in dev_deps.items():
            dependency = self._parse_poetry_package_spec(package_name, package_spec, is_dev=True)
            if dependency:
                dependencies.append(dependency)
        
        # Parse group dependencies (Poetry 1.2+)
        groups = poetry_section.get('group', {})
        for group_name, group_data in groups.items():
            is_dev = group_name in ['dev', 'test', 'docs']  # Common dev group names
            group_deps = group_data.get('dependencies', {})
            
            for package_name, package_spec in group_deps.items():
                dependency = self._parse_poetry_package_spec(package_name, package_spec, is_dev=is_dev)
                if dependency:
                    dependencies.append(dependency)
        
        return dependencies
    
    def _parse_pdm_dependencies(self, project_section: Dict[str, Any]) -> List[Dependency]:
        """Parse PDM dependencies from pyproject.toml"""
        dependencies: List[Dependency] = []
        
        # Parse production dependencies
        deps = project_section.get('dependencies', [])
        for dep_str in deps:
            dependency = self._parse_requirement_string(dep_str, is_dev=False)
            if dependency:
                dependencies.append(dependency)
        
        # Parse optional dependencies (often used for dev dependencies)
        optional_deps = project_section.get('optional-dependencies', {})
        for group_name, group_deps in optional_deps.items():
            is_dev = group_name in ['dev', 'test', 'docs', 'lint']  # Common dev group names
            
            for dep_str in group_deps:
                dependency = self._parse_requirement_string(dep_str, is_dev=is_dev)
                if dependency:
                    dependencies.append(dependency)
        
        return dependencies
    
    def _parse_flit_dependencies(self, flit_section: Dict[str, Any]) -> List[Dependency]:
        """Parse Flit dependencies from pyproject.toml"""
        dependencies: List[Dependency] = []
        
        # Flit uses module.metadata to point to module metadata
        # This is a simplified parser
        metadata = flit_section.get('metadata', {})
        
        # Parse requires
        requires = metadata.get('requires', [])
        for dep_str in requires:
            dependency = self._parse_requirement_string(dep_str, is_dev=False)
            if dependency:
                dependencies.append(dependency)
        
        # Parse requires-extra (dev dependencies)
        requires_extra = metadata.get('requires-extra', {})
        for group_name, group_deps in requires_extra.items():
            is_dev = group_name in ['dev', 'test', 'docs']  # Common dev group names
            
            for dep_str in group_deps:
                dependency = self._parse_requirement_string(dep_str, is_dev=is_dev)
                if dependency:
                    dependencies.append(dependency)
        
        return dependencies
    
    def _parse_poetry_package_spec(self, package_name: str, package_spec: Any, is_dev: bool) -> Optional[Dependency]:
        """Parse a Poetry package specification"""
        try:
            if isinstance(package_spec, str):
                # Simple version string
                version_spec = self._parse_poetry_version_string(package_spec)
                return Dependency(
                    name=package_name,
                    version_spec=version_spec,
                    extras=[],
                    is_dev=is_dev
                )
            
            elif isinstance(package_spec, dict):
                # Complex specification
                version = package_spec.get('version')
                extras = package_spec.get('extras', [])
                
                # Handle git/URL/path specifications
                if any(key in package_spec for key in ['git', 'url', 'path', 'develop']):
                    return Dependency(
                        name=package_name,
                        version_spec=None,  # Git/path deps don't have version specs
                        extras=extras if isinstance(extras, list) else [],
                        is_dev=is_dev
                    )
                
                version_spec = self._parse_poetry_version_string(version) if version else None
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
    
    def _parse_poetry_version_string(self, version_str: str) -> Optional[SpecifierSet]:
        """Parse a Poetry version string into a SpecifierSet"""
        if not version_str or version_str == '*':
            return None
        
        try:
            # Poetry uses ^ and ~ which are not standard pip specifiers
            # Convert them to standard specifiers
            if version_str.startswith('^'):
                # Caret operator: ^1.2.3 means >=1.2.3, <2.0.0
                version = version_str[1:]
                parts = version.split('.')
                if len(parts) >= 1:
                    major = int(parts[0])
                    next_major = major + 1
                    return SpecifierSet(f">={version}, <{next_major}.0.0")
            
            elif version_str.startswith('~'):
                # Tilde operator: ~1.2.3 means >=1.2.3, <1.3.0
                version = version_str[1:]
                parts = version.split('.')
                if len(parts) >= 2:
                    major = int(parts[0])
                    minor = int(parts[1])
                    next_minor = minor + 1
                    return SpecifierSet(f">={version}, <{major}.{next_minor}.0")
                elif len(parts) == 1:
                    major = int(parts[0])
                    next_major = major + 1
                    return SpecifierSet(f">={version}, <{next_major}.0")
            
            else:
                # Handle plain version numbers by adding ==
                if version_str.replace('.', '').replace('-', '').replace('+', '').isdigit() or version_str[0].isdigit():
                    version_str = f"=={version_str}"
                # Standard specifier
                return SpecifierSet(version_str)
        
        except Exception as e:
            self.logger.warning(f"Could not parse Poetry version string '{version_str}': {e}")
            return None
    
    def _parse_requirement_string(self, req_str: str, is_dev: bool) -> Optional[Dependency]:
        """Parse a requirement string (PEP 508 format)"""
        try:
            from packaging.requirements import Requirement
            requirement = Requirement(req_str)
            
            return Dependency(
                name=requirement.name,
                version_spec=requirement.specifier if requirement.specifier else None,
                extras=list(requirement.extras),
                is_dev=is_dev
            )
        
        except Exception as e:
            self.logger.warning(f"Could not parse requirement string '{req_str}': {e}")
            return None
