# Usage Examples

This directory contains practical examples demonstrating the capabilities of the Python Dependency Reader tool across different scenarios and project types.

## 📋 Example Categories

### Basic Usage Examples
- Simple dependency file parsing
- Python source code scanning
- Package information lookup

### Advanced Analysis Examples  
- Multi-format conflict detection
- Large project analysis
- CI/CD integration patterns

### Real-World Scenarios
- Django project analysis
- FastAPI application scanning
- Data science project dependencies

## 🔍 Parse Command Examples

### Example 1: Basic Dependency File Parsing
```bash
# Parse requirements.txt in current directory
python main.py parse

# Output:
# ✓ Found 1 dependency file
# ✓ requirements.txt: 12 dependencies
# 
# Dependencies found:
# • requests (>=2.25.0)
# • django (>=4.0,<5.0)
# • psycopg2-binary (==2.9.5)
```

### Example 2: Multi-Format Analysis
```bash
# Parse all supported formats recursively
python main.py parse --recursive --format table

# Output:
# ┌─────────────────┬─────────────┬──────────────────┬──────────────┐
# │ Package         │ Version     │ File             │ Type         │
# ├─────────────────┼─────────────┼──────────────────┼──────────────┤
# │ requests        │ >=2.25.0    │ requirements.txt │ Production   │
# │ django          │ ^4.0        │ pyproject.toml   │ Production   │
# │ pytest          │ ^7.0.0      │ Pipfile          │ Development  │
# │ black           │ ==22.12.0   │ requirements.txt │ Production   │
# └─────────────────┴─────────────┴──────────────────┴──────────────┘
```

### Example 3: Conflict Detection
```bash
# Detect version conflicts across files
python main.py parse --detect-conflicts --check-pypi

# Output:
# ✓ Found 3 dependency files
# ✓ Total dependencies: 24
# ⚠ Version conflicts detected:
# 
# • requests:
#     requirements.txt: >=2.25.0
#     pyproject.toml: ^2.28.0
#     Status: Compatible (latest: 2.31.0)
# 
# • django:
#     requirements.txt: >=4.0,<5.0
#     Pipfile: "^3.2"
#     Status: ❌ Incompatible ranges
```

## 📄 Scan Command Examples

### Example 4: Python Source Analysis
```bash
# Scan Python files in src directory
python main.py scan --path ./src --recursive

# Output:
# ✓ Scanning recursively in directory: ./src
# ✓ Found dependencies in 15 Python file(s)
# ✓ Dependencies saved to dependencies.txt
# 
# Unique packages found:
# • requests (used in 8 files)
# • pandas (used in 5 files)
# • numpy (used in 12 files)
# • matplotlib (used in 3 files)
```

### Example 5: Custom Log File
```bash
# Save analysis to custom log file with PyPI validation
python main.py scan --path ./myproject --recursive --log analysis_2024.txt --check-pypi

# Output:
# ✓ Scanning recursively in directory: ./myproject
# ✓ Found dependencies in 23 Python file(s)
# ✓ Dependencies saved to analysis_2024.txt
# ✓ Fetching package information from PyPI...
# 
# PyPI Status:
# • requests: Latest version on PyPI is 2.31.0
# • pandas: Latest version on PyPI is 2.1.4
# • numpy: Latest version on PyPI is 1.26.2
```

### Generated Log File Content:
```txt
# Python Dependencies Analysis
# Generated on: 2024-01-15 14:30:22
# Total files analyzed: 23

## Summary
Total unique packages found: 8

## Package Usage
- requests (used in 8 file(s))
  - ./myproject/api/client.py
  - ./myproject/utils/http.py
  - ./myproject/tests/test_api.py
- pandas (used in 5 file(s))
  - ./myproject/data/processor.py
  - ./myproject/analytics/report.py

## Detailed Analysis

### ./myproject/api/client.py
- requests
- json
- logging

### ./myproject/data/processor.py
- pandas
- numpy
- pathlib
```

## 📦 Info Command Examples

### Example 6: Package Information Lookup
```bash
# Get detailed package information
python main.py info requests

# Output:
# Package: requests
# Version: 2.31.0
# Author: Kenneth Reitz
# Summary: Python HTTP for Humans.
# Homepage: https://requests.readthedocs.io
# License: Apache 2.0
# 
# Dependencies:
# • charset-normalizer >=2,<4
# • idna >=2.5,<4
# • urllib3 >=1.21.1,<3
# • certifi >=2017.4.17
```

## 🏗️ Real-World Project Examples

### Django Web Application
```bash
# Comprehensive Django project analysis
cd django_project/
python main.py parse --recursive --detect-conflicts --format json > deps.json
python main.py scan --path . --recursive --log django_analysis.txt

# Typical Django dependencies found:
# Production: django, psycopg2-binary, redis, celery
# Development: pytest-django, black, flake8, coverage
# Python imports: os, sys, django, rest_framework
```

### Data Science Project
```bash
# Analyze Jupyter notebook project
cd data_science_project/
python main.py scan --path ./notebooks --recursive --check-pypi
python main.py parse --path ./requirements --recursive

# Common data science packages:
# • pandas, numpy, matplotlib, seaborn
# • scikit-learn, tensorflow, pytorch
# • jupyter, ipython, notebook
```

### FastAPI Microservice
```bash
# FastAPI application analysis
cd fastapi_service/
python main.py parse --check-pypi --format table
python main.py scan --path ./app --recursive --log api_deps.txt

# FastAPI stack typically includes:
# • fastapi, uvicorn, pydantic
# • sqlalchemy, alembic
# • pytest, httpx (testing)
```

## 🔧 Advanced Usage Patterns

### CI/CD Integration
```bash
# Dependency audit in CI pipeline
python main.py parse --format json --check-pypi > dependency_report.json
python main.py scan --recursive --log security_audit.txt

# Use exit codes for automation
if python main.py parse --detect-conflicts --quiet; then
    echo "No conflicts detected"
else
    echo "Version conflicts found!"
    exit 1
fi
```

### Development Workflow
```bash
# Pre-commit dependency check
python main.py scan --path ./src --format simple | grep -v "test_"

# New feature dependency analysis
python main.py scan --path ./feature_branch --recursive --log feature_deps.txt

# Dependency cleanup verification
python main.py parse --detect-conflicts
```

### Performance Analysis
```bash
# Large codebase scanning
time python main.py scan --path ./large_project --recursive --format simple

# Memory-efficient processing
python main.py scan --path ./huge_project --format json | jq '.files | length'
```

## 📊 Output Format Examples

### JSON Output (Machine Processing)
```bash
python main.py parse --format json | jq '.files[0].dependencies[0]'

# Output:
{
  "name": "requests",
  "version_spec": ">=2.25.0",
  "extras": [],
  "is_dev": false
}
```

### Table Output (Human Readable)
```bash
python main.py scan --path ./src --format table

# Clean tabular output for reports
```

### Simple Output (Scripting)
```bash
# Extract just package names
python main.py scan --format simple | cut -d' ' -f1 | sort | uniq

# Count dependencies
python main.py scan --format simple | wc -l
```

## 🚨 Error Handling Examples

### Network Issues
```bash
# Handle PyPI connectivity problems
python main.py info requests
# If network fails: graceful degradation with cached data

python main.py parse --check-pypi
# Continues analysis even if PyPI is unreachable
```

### File Access Issues
```bash
# Handle permission denied
python main.py scan --path /restricted/directory
# Warning: Could not access directory, skipping

# Handle malformed files
python main.py parse --path ./broken_requirements.txt
# Warning: Could not parse file, continuing with others
```

### Large File Handling
```bash
# Process very large codebases
python main.py scan --path ./million_files --recursive
# Uses streaming and memory-efficient processing
```

## 💡 Tips and Best Practices

### Performance Optimization
```bash
# Cache PyPI results for repeated analysis
export DEPENDENCY_READER_CACHE_TTL=7200
python main.py parse --check-pypi  # First run
python main.py parse --check-pypi  # Subsequent runs use cache

# Use simple format for scripting
python main.py scan --format simple > deps.txt
```

### Integration Patterns
```bash
# Combine with other tools
python main.py parse --format json | jq '.files[].dependencies[].name' | safety check

# Version pinning workflow
python main.py scan --check-pypi | grep "Latest version" > pin_candidates.txt
```

### Debugging and Troubleshooting
```bash
# Enable verbose output for debugging
python main.py -v scan --path ./problem_directory

# Test specific file parsing
python main.py parse --path ./specific/requirements.txt -v
```

---

*These examples demonstrate the versatility and power of the Python Dependency Reader for various development workflows and project types.*