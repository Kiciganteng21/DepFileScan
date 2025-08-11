"""
Parser for requirements.txt files
"""

import re
import logging
from pathlib import Path
from typing import List, Optional, Set, Tuple
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

from ..models import DependencyFile, Dependency


class RequirementsParser:
    """Parser for requirements.txt files"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Patterns for different line types
        self.comment_pattern = re.compile(r'^\s*#')
        self.blank_pattern = re.compile(r'^\s*$')
        self.url_pattern = re.compile(r'^(https?|git\+|hg\+|svn\+|bzr\+)')
        self.editable_pattern = re.compile(r'^\s*-e\s+')
        self.requirement_file_pattern = re.compile(r'^\s*-r\s+(.+)')
        self.constraint_file_pattern = re.compile(r'^\s*-c\s+(.+)')
        self.index_url_pattern = re.compile(r'^\s*--index-url\s+')
        self.extra_index_url_pattern = re.compile(r'^\s*--extra-index-url\s+')
        self.find_links_pattern = re.compile(r'^\s*--find-links\s+')
        self.trusted_host_pattern = re.compile(r'^\s*--trusted-host\s+')
    
    def parse(self, file_path: Path) -> DependencyFile:
        """Parse a requirements.txt file"""
        self.logger.debug(f"Parsing requirements.txt file: {file_path}")
        
        dependencies: List[Dependency] = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                try:
                    dependency = self._parse_line(line.strip(), line_num)
                    if dependency:
                        dependencies.append(dependency)
                except Exception as e:
                    self.logger.warning(f"Error parsing line {line_num} in {file_path}: {e}")
                    continue
        
        except Exception as e:
            self.logger.error(f"Error reading requirements.txt file {file_path}: {e}")
            raise
        
        self.logger.info(f"Parsed {len(dependencies)} dependencies from {file_path}")
        
        return DependencyFile(
            file_path=file_path,
            file_type="requirements.txt",
            dependencies=dependencies
        )
    
    def _parse_line(self, line: str, line_num: int) -> Optional[Dependency]:
        """Parse a single line from requirements.txt"""
        # Skip comments and blank lines
        if self.comment_pattern.match(line) or self.blank_pattern.match(line):
            return None
        
        # Skip pip options
        if (self.index_url_pattern.match(line) or 
            self.extra_index_url_pattern.match(line) or
            self.find_links_pattern.match(line) or
            self.trusted_host_pattern.match(line)):
            return None
        
        # Handle -r (requirement files) and -c (constraint files)
        req_match = self.requirement_file_pattern.match(line)
        const_match = self.constraint_file_pattern.match(line)
        if req_match or const_match:
            self.logger.debug(f"Skipping requirement/constraint file reference: {line}")
            return None
        
        # Handle editable packages
        if self.editable_pattern.match(line):
            line = self.editable_pattern.sub('', line).strip()
            self.logger.debug(f"Processing editable package: {line}")
        
        # Handle direct URLs
        if self.url_pattern.match(line):
            return self._parse_url_requirement(line)
        
        # Parse standard requirement
        try:
            requirement = Requirement(line)
            return self._requirement_to_dependency(requirement)
        except Exception as e:
            self.logger.warning(f"Could not parse requirement '{line}': {e}")
            return None
    
    def _parse_url_requirement(self, line: str) -> Optional[Dependency]:
        """Parse URL-based requirements"""
        # Extract package name from URL if possible
        # This is a simplified approach - in practice, URL requirements are complex
        
        # Look for egg= parameter
        if '#egg=' in line:
            egg_part = line.split('#egg=')[1].split('&')[0]
            # Handle egg names with extras: package_name[extra1,extra2]
            if '[' in egg_part:
                name = egg_part.split('[')[0]
                extras_part = egg_part.split('[')[1].rstrip(']')
                extras = [e.strip() for e in extras_part.split(',') if e.strip()]
            else:
                name = egg_part
                extras = []
            
            return Dependency(
                name=name,
                version_spec=None,  # URL requirements don't have version specs
                extras=extras,
                is_dev=False
            )
        
        # If no egg name, try to extract from URL path
        url_parts = line.split('/')
        if url_parts:
            potential_name = url_parts[-1]
            # Remove common suffixes
            for suffix in ['.git', '.tar.gz', '.zip', '.whl']:
                if potential_name.endswith(suffix):
                    potential_name = potential_name[:-len(suffix)]
                    break
            
            if potential_name:
                return Dependency(
                    name=potential_name,
                    version_spec=None,
                    extras=[],
                    is_dev=False
                )
        
        self.logger.warning(f"Could not extract package name from URL: {line}")
        return None
    
    def _requirement_to_dependency(self, requirement: Requirement) -> Dependency:
        """Convert a packaging.requirements.Requirement to a Dependency"""
        return Dependency(
            name=requirement.name,
            version_spec=requirement.specifier if requirement.specifier else None,
            extras=list(requirement.extras),
            is_dev=False  # requirements.txt doesn't distinguish dev dependencies
        )
