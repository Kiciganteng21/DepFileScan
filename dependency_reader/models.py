"""
Data models for dependency information
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Set
from packaging.specifiers import SpecifierSet


@dataclass
class Dependency:
    """Represents a single dependency"""
    name: str
    version_spec: Optional[SpecifierSet]
    extras: List[str]
    is_dev: bool
    
    def __str__(self) -> str:
        """String representation of the dependency"""
        extras_str = f"[{','.join(self.extras)}]" if self.extras else ""
        version_str = f" {self.version_spec}" if self.version_spec else ""
        dev_str = " [DEV]" if self.is_dev else ""
        return f"{self.name}{extras_str}{version_str}{dev_str}"
    
    def __eq__(self, other) -> bool:
        """Check equality based on name and dev status"""
        if not isinstance(other, Dependency):
            return False
        return self.name.lower() == other.name.lower() and self.is_dev == other.is_dev
    
    def __hash__(self) -> int:
        """Hash based on name and dev status"""
        return hash((self.name.lower(), self.is_dev))


@dataclass
class DependencyFile:
    """Represents a dependency file and its parsed dependencies"""
    file_path: Path
    file_type: str  # "requirements.txt", "Pipfile", "pyproject.toml"
    dependencies: List[Dependency]
    
    def get_dependency_names(self) -> Set[str]:
        """Get set of all dependency names in this file"""
        return {dep.name.lower() for dep in self.dependencies}
    
    def get_production_dependencies(self) -> List[Dependency]:
        """Get only production dependencies"""
        return [dep for dep in self.dependencies if not dep.is_dev]
    
    def get_dev_dependencies(self) -> List[Dependency]:
        """Get only development dependencies"""
        return [dep for dep in self.dependencies if dep.is_dev]
    
    def find_dependency(self, name: str, is_dev: Optional[bool] = None) -> Optional[Dependency]:
        """Find a dependency by name"""
        name_lower = name.lower()
        for dep in self.dependencies:
            if dep.name.lower() == name_lower:
                if is_dev is None or dep.is_dev == is_dev:
                    return dep
        return None


@dataclass
class VersionConflict:
    """Represents a version conflict for a specific package"""
    file_path: Path
    file_type: str
    version_spec: Optional[SpecifierSet]
    is_dev: bool
    
    def __str__(self) -> str:
        """String representation of the version conflict"""
        version_str = str(self.version_spec) if self.version_spec else "any version"
        dev_str = " [DEV]" if self.is_dev else ""
        return f"{self.file_path}: {version_str}{dev_str}"


@dataclass
class ConflictReport:
    """Represents a conflict report for a package across multiple files"""
    package_name: str
    version_conflicts: List[VersionConflict]
    
    def __str__(self) -> str:
        """String representation of the conflict report"""
        conflicts_str = '\n'.join(f"  - {conflict}" for conflict in self.version_conflicts)
        return f"Conflict for {self.package_name}:\n{conflicts_str}"
    
    def has_version_conflicts(self) -> bool:
        """Check if there are actual version specification conflicts"""
        version_specs = [vc.version_spec for vc in self.version_conflicts if vc.version_spec]
        return len(set(str(spec) for spec in version_specs)) > 1
    
    def has_dev_prod_conflicts(self) -> bool:
        """Check if the same package appears in both dev and prod dependencies"""
        has_dev = any(vc.is_dev for vc in self.version_conflicts)
        has_prod = any(not vc.is_dev for vc in self.version_conflicts)
        return has_dev and has_prod


@dataclass
class PackageInfo:
    """Represents package information from PyPI"""
    name: str
    version: str
    summary: Optional[str]
    description: Optional[str]
    author: Optional[str]
    license: Optional[str]
    homepage: Optional[str]
    requires_dist: List[str]
    requires_python: Optional[str]
    
    @classmethod
    def from_pypi_json(cls, pypi_data: dict) -> 'PackageInfo':
        """Create PackageInfo from PyPI JSON response"""
        info = pypi_data.get('info', {})
        
        return cls(
            name=info.get('name', ''),
            version=info.get('version', ''),
            summary=info.get('summary'),
            description=info.get('description'),
            author=info.get('author'),
            license=info.get('license'),
            homepage=info.get('home_page'),
            requires_dist=info.get('requires_dist', []) or [],
            requires_python=info.get('requires_python')
        )
