
"""
Shared test fixtures and configuration
"""

import pytest
import tempfile
from pathlib import Path
from dependency_reader.models import Dependency
from packaging.specifiers import SpecifierSet


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_dependencies():
    """Create sample dependencies for testing"""
    return [
        Dependency(
            name="requests",
            version_spec=SpecifierSet(">=2.25.0"),
            is_dev=False,
            extras=[]
        ),
        Dependency(
            name="flask",
            version_spec=SpecifierSet(">=2.0.0"),
            is_dev=False,
            extras=[]
        ),
        Dependency(
            name="pytest",
            version_spec=SpecifierSet(">=7.0.0"),
            is_dev=True,
            extras=[]
        ),
        Dependency(
            name="black",
            version_spec=SpecifierSet(">=22.0.0"),
            is_dev=True,
            extras=[]
        ),
    ]
