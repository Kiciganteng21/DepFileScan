
"""
Performance benchmarks for dependency reader
"""

import pytest
import tempfile
import time
from pathlib import Path
from dependency_reader.parsers.requirements import RequirementsParser
from dependency_reader.parsers.pipfile_parser import PipfileParser
from dependency_reader.parsers.pyproject_parser import PyprojectParser
from dependency_reader.python_scanner import PythonScanner
from dependency_reader.conflict_detector import ConflictDetector


class TestParsingPerformance:
    """Performance tests for parsing operations"""
    
    def test_requirements_parsing_performance(self, benchmark, temp_dir):
        """Benchmark requirements.txt parsing"""
        # Create a large requirements file
        req_file = temp_dir / "requirements.txt"
        requirements_content = "\n".join([
            f"package{i}>=1.{i}.0" for i in range(1000)
        ])
        req_file.write_text(requirements_content)
        
        parser = RequirementsParser()
        
        def parse_requirements():
            return parser.parse(req_file)
        
        result = benchmark(parse_requirements)
        assert result is not None
        assert len(result.dependencies) == 1000
    
    def test_python_scanning_performance(self, benchmark, temp_dir):
        """Benchmark Python file scanning"""
        # Create multiple Python files with imports
        for i in range(50):
            py_file = temp_dir / f"module_{i}.py"
            imports_content = "\n".join([
                f"import package_{j}" for j in range(20)
            ])
            py_file.write_text(imports_content)
        
        scanner = PythonScanner()
        
        def scan_directory():
            return scanner.scan_directory(temp_dir, recursive=True)
        
        result = benchmark(scan_directory)
        assert len(result) == 50
    
    def test_conflict_detection_performance(self, benchmark, sample_dependencies):
        """Benchmark conflict detection"""
        from dependency_reader.models import DependencyFile
        
        # Create multiple dependency files with potential conflicts
        dependency_files = []
        for i in range(10):
            dep_file = DependencyFile(
                file_path=Path(f"requirements_{i}.txt"),
                file_type="requirements.txt",
                dependencies=sample_dependencies * 5  # Multiply to create more dependencies
            )
            dependency_files.append(dep_file)
        
        detector = ConflictDetector()
        
        def detect_conflicts():
            return detector.detect_conflicts(dependency_files)
        
        result = benchmark(detect_conflicts)
        assert isinstance(result, list)


class TestScalingPerformance:
    """Test performance with different scales of data"""
    
    @pytest.mark.parametrize("num_deps", [10, 100, 500, 1000])
    def test_requirements_parsing_scale(self, benchmark, temp_dir, num_deps):
        """Test parsing performance with different numbers of dependencies"""
        req_file = temp_dir / "requirements.txt"
        requirements_content = "\n".join([
            f"package{i}>=1.{i % 10}.0" for i in range(num_deps)
        ])
        req_file.write_text(requirements_content)
        
        parser = RequirementsParser()
        
        def parse_requirements():
            return parser.parse(req_file)
        
        result = benchmark(parse_requirements)
        assert len(result.dependencies) == num_deps
    
    @pytest.mark.parametrize("num_files", [5, 25, 50, 100])
    def test_scanning_scale(self, benchmark, temp_dir, num_files):
        """Test scanning performance with different numbers of files"""
        for i in range(num_files):
            py_file = temp_dir / f"module_{i}.py"
            py_file.write_text("import requests\nimport click\nimport pandas")
        
        scanner = PythonScanner()
        
        def scan_directory():
            return scanner.scan_directory(temp_dir, recursive=True)
        
        result = benchmark(scan_directory)
        assert len(result) == num_files


class TestMemoryEfficiency:
    """Test memory usage patterns"""
    
    def test_large_file_parsing_memory(self, temp_dir):
        """Test memory usage when parsing large files"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create a very large requirements file
        req_file = temp_dir / "large_requirements.txt"
        requirements_content = "\n".join([
            f"very-long-package-name-{i}>=1.{i % 100}.{i % 10}" 
            for i in range(5000)
        ])
        req_file.write_text(requirements_content)
        
        parser = RequirementsParser()
        result = parser.parse(req_file)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB for this test)
        assert memory_increase < 50 * 1024 * 1024  # 50MB
        assert len(result.dependencies) == 5000


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_dependencies():
    """Create sample dependencies for testing"""
    from dependency_reader.models import Dependency
    from packaging.specifiers import SpecifierSet
    
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


if __name__ == "__main__":
    pytest.main([__file__, "--benchmark-only"])
