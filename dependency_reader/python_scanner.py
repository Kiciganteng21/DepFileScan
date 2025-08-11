"""
Python file scanner for extracting dependencies from import statements
"""

import ast
import logging
import re
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple
from dataclasses import dataclass

from .models import Dependency, DependencyFile
from packaging.specifiers import SpecifierSet


@dataclass
class ImportInfo:
    """Information about an import statement"""
    module_name: str
    alias: Optional[str]
    from_import: bool
    line_number: int
    is_relative: bool


class PythonScanner:
    """Scanner for extracting dependencies from Python source files"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Standard library modules (Python 3.11)
        self.stdlib_modules = {
            'abc', 'argparse', 'array', 'ast', 'asyncio', 'base64', 'bisect',
            'builtins', 'calendar', 'collections', 'concurrent', 'configparser',
            'contextlib', 'copy', 'csv', 'datetime', 'decimal', 'difflib',
            'email', 'enum', 'errno', 'fcntl', 'fileinput', 'fnmatch',
            'fractions', 'functools', 'gc', 'glob', 'gzip', 'hashlib',
            'heapq', 'hmac', 'html', 'http', 'importlib', 'inspect', 'io',
            'ipaddress', 'itertools', 'json', 'keyword', 'locale', 'logging',
            'lzma', 'math', 'mimetypes', 'multiprocessing', 'operator', 'os',
            'pathlib', 'pickle', 'platform', 'pprint', 'queue', 'random',
            're', 'shutil', 'signal', 'socket', 'sqlite3', 'ssl', 'statistics',
            'string', 'subprocess', 'sys', 'tarfile', 'tempfile', 'textwrap',
            'threading', 'time', 'traceback', 'types', 'typing', 'unittest',
            'urllib', 'uuid', 'warnings', 'weakref', 'xml', 'zipfile', 'zlib'
        }
    
    def scan_directory(self, path: Path, recursive: bool = False) -> List[DependencyFile]:
        """Scan a directory for Python files and extract dependencies"""
        self.logger.debug(f"Scanning directory: {path}")
        
        python_files = self._find_python_files(path, recursive)
        dependency_files = []
        
        for py_file in python_files:
            dependencies = self._analyze_python_file(py_file)
            if dependencies:
                dep_file = DependencyFile(
                    file_path=py_file,
                    file_type="python",
                    dependencies=dependencies
                )
                dependency_files.append(dep_file)
        
        return dependency_files
    
    def scan_file(self, file_path: Path) -> Optional[DependencyFile]:
        """Scan a single Python file for dependencies"""
        if not file_path.suffix == '.py':
            self.logger.warning(f"File {file_path} is not a Python file")
            return None
        
        dependencies = self._analyze_python_file(file_path)
        if dependencies:
            return DependencyFile(
                file_path=file_path,
                file_type="python",
                dependencies=dependencies
            )
        return None
    
    def _find_python_files(self, path: Path, recursive: bool) -> List[Path]:
        """Find all Python files in the given path"""
        python_files = []
        
        if recursive:
            pattern = "**/*.py"
        else:
            pattern = "*.py"
        
        for py_file in path.glob(pattern):
            if py_file.is_file() and not self._should_ignore_file(py_file):
                python_files.append(py_file)
        
        return python_files
    
    def _should_ignore_file(self, file_path: Path) -> bool:
        """Check if a Python file should be ignored"""
        ignore_patterns = {
            '__pycache__', '.git', '.tox', '.venv', 'venv', 'env',
            'build', 'dist', '.eggs', '.pytest_cache', 'node_modules'
        }
        
        # Check if any parent directory matches ignore patterns
        for part in file_path.parts:
            if part in ignore_patterns:
                return True
        
        # Ignore files that start with test_ or end with _test.py
        if file_path.name.startswith('test_') or file_path.name.endswith('_test.py'):
            return True
        
        return False
    
    def _analyze_python_file(self, file_path: Path) -> List[Dependency]:
        """Analyze a Python file and extract dependencies"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the AST
            tree = ast.parse(content, filename=str(file_path))
            imports = self._extract_imports(tree)
            
            # Convert imports to dependencies
            dependencies = self._imports_to_dependencies(imports)
            
            self.logger.debug(f"Found {len(dependencies)} dependencies in {file_path}")
            return dependencies
        
        except (SyntaxError, UnicodeDecodeError) as e:
            self.logger.warning(f"Could not parse {file_path}: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error analyzing {file_path}: {e}")
            return []
    
    def _extract_imports(self, tree: ast.AST) -> List[ImportInfo]:
        """Extract import information from AST"""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(ImportInfo(
                        module_name=alias.name,
                        alias=alias.asname,
                        from_import=False,
                        line_number=node.lineno,
                        is_relative=False
                    ))
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(ImportInfo(
                        module_name=node.module,
                        alias=None,
                        from_import=True,
                        line_number=node.lineno,
                        is_relative=node.level > 0
                    ))
        
        return imports
    
    def _imports_to_dependencies(self, imports: List[ImportInfo]) -> List[Dependency]:
        """Convert import information to dependency objects"""
        package_names = set()
        
        for import_info in imports:
            # Skip relative imports
            if import_info.is_relative:
                continue
            
            # Get the top-level package name
            top_level_package = import_info.module_name.split('.')[0]
            
            # Skip standard library modules
            if top_level_package in self.stdlib_modules:
                continue
            
            # Skip common built-in or local patterns
            if self._is_builtin_or_local(top_level_package):
                continue
            
            package_names.add(top_level_package)
        
        # Convert to Dependency objects
        dependencies = []
        for package_name in sorted(package_names):
            dependencies.append(Dependency(
                name=package_name,
                version_spec=None,  # Can't determine version from imports
                extras=[],
                is_dev=False
            ))
        
        return dependencies
    
    def _is_builtin_or_local(self, package_name: str) -> bool:
        """Check if a package is likely built-in or local"""
        # Common patterns for local or built-in modules
        builtin_patterns = {
            # Single character names (often local)
            '_', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l',
            'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
        }
        
        if package_name in builtin_patterns:
            return True
        
        # Skip very short names that are likely local
        if len(package_name) <= 2:
            return True
        
        return False
    
    def merge_dependencies_by_package(self, dependency_files: List[DependencyFile]) -> Dict[str, List[Path]]:
        """Merge dependencies by package name across all files"""
        package_files = {}
        
        for dep_file in dependency_files:
            for dependency in dep_file.dependencies:
                if dependency.name not in package_files:
                    package_files[dependency.name] = []
                package_files[dependency.name].append(dep_file.file_path)
        
        return package_files