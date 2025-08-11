# Python Dependency Reader

A comprehensive CLI tool that reads, parses, and analyzes multiple dependency file formats commonly used in Python projects. The tool supports requirements.txt, Pipfile, and pyproject.toml files, providing unified dependency analysis with conflict detection capabilities and PyPI integration for package validation.

![Architecture](docs/images/architecture.svg)

## Features

### 🔍 **Multi-Format Support**
- **requirements.txt**: Full pip requirements format support
- **Pipfile**: Native Pipfile parsing with fallback
- **pyproject.toml**: Poetry, PDM, and Flit formats
- **Python Source**: AST-based import analysis

### ⚡ **Powerful Analysis**
- **Conflict Detection**: Cross-file version conflicts
- **PyPI Integration**: Package validation and latest version checking
- **Recursive Scanning**: Deep directory traversal
- **Smart Filtering**: Ignores common non-dependency directories

### 📊 **Rich Output**
- **Multiple Formats**: JSON, Table, Simple text
- **Colored Output**: Enhanced visual feedback
- **Logging**: Detailed analysis logs with timestamps
- **Export**: Save results to custom log files

## Quick Start

### Installation

```bash
# Install dependencies
pip install click colorlog packaging requests toml

# Run the tool
python main.py --help
```

### Basic Usage

```bash
# Parse dependency files in current directory
python main.py parse

# Scan Python files for imports
python main.py scan --path ./src --recursive

# Get package information from PyPI
python main.py info requests

# Advanced scanning with logging
python main.py scan --path ./project --recursive --log analysis.txt --check-pypi
```

## Commands

### `parse` - Parse Dependency Files
Analyzes traditional dependency files (requirements.txt, Pipfile, pyproject.toml)

```bash
python main.py parse [OPTIONS]

Options:
  -p, --path PATH        Directory to scan (default: current)
  -r, --recursive        Search subdirectories
  -f, --format FORMAT    Output format (json|table|simple)
  --check-pypi          Validate packages against PyPI
  --detect-conflicts    Find version conflicts between files
```

### `scan` - Scan Python Source Files
Extracts dependencies from Python import statements using AST analysis

```bash
python main.py scan [OPTIONS]

Options:
  -p, --path PATH        File or directory to scan
  -r, --recursive        Scan subdirectories recursively
  -l, --log FILENAME     Save results to log file (default: dependencies.txt)
  -f, --format FORMAT    Output format (json|table|simple)
  --check-pypi          Check PyPI for latest versions
```

### `info` - Package Information
Retrieve detailed information about a specific package from PyPI

```bash
python main.py info PACKAGE_NAME
```

## Architecture

![Workflow](docs/images/workflow.svg)

### Core Components

- **Parser System**: Modular parsers for each file format
- **Python Scanner**: AST-based import extraction
- **Conflict Detector**: Cross-file dependency analysis
- **PyPI Client**: Rate-limited API integration with caching
- **CLI Interface**: Click-based command structure

### Design Patterns

- **Strategy Pattern**: File format handling
- **Factory Pattern**: Parser selection
- **Repository Pattern**: PyPI API abstraction

## Project Structure

```
dependency_reader/
├── cli.py                  # Main CLI interface
├── models.py              # Data structures
├── conflict_detector.py   # Version conflict analysis
├── pypi_client.py        # PyPI API integration
├── python_scanner.py     # Python source analysis
├── utils.py              # Common utilities
└── parsers/              # File format parsers
    ├── requirements.py   # requirements.txt
    ├── pipfile_parser.py # Pipfile support
    └── pyproject_parser.py # pyproject.toml
```

## Examples

### Scan Python Project
```bash
# Analyze a Django project recursively
python main.py scan --path ./myproject --recursive --log django_deps.txt

# Output saved to django_deps.txt:
# Python Dependencies Analysis
# Generated on: 2025-01-15 14:30:22
# Total files analyzed: 23
#
# ## Summary
# Total unique packages found: 15
#
# ## Package Usage
# - django (used in 8 file(s))
# - requests (used in 3 file(s))
# - celery (used in 2 file(s))
```

### Parse Multiple Formats
```bash
# Find conflicts across different dependency files
python main.py parse --recursive --detect-conflicts --check-pypi

# Output:
# ✓ Found 3 dependency files
# ✓ requirements.txt: 12 dependencies
# ✓ pyproject.toml: 8 dependencies
# ⚠ Version conflicts detected:
#   • requests: 
#     requirements.txt: >=2.25.0
#     pyproject.toml: ^2.28.0
```

### PyPI Integration
```bash
# Check package information
python main.py info fastapi

# Output:
# Package: fastapi
# Version: 0.104.1
# Author: Sebastián Ramírez
# Summary: FastAPI framework, high performance, easy to learn...
```

## Advanced Features

### Conflict Detection
The tool automatically detects version conflicts across different dependency files:
- Compares version specifications using packaging library standards
- Identifies dev vs production dependency mismatches
- Reports conflicts with file locations and version requirements

### PyPI Integration
- **Rate Limiting**: Respects PyPI API limits
- **Caching**: Local filesystem cache for responses
- **Retry Logic**: Robust error handling with exponential backoff
- **Package Validation**: Verifies package existence and versions

### Smart Filtering
Automatically ignores common directories and files:
- Version control: `.git`, `.svn`
- Virtual environments: `.venv`, `venv`, `env`
- Build artifacts: `build`, `dist`, `.eggs`
- Cache directories: `__pycache__`, `.pytest_cache`
- Package managers: `node_modules`

## Output Formats

### Table Format (Default)
```
┌─────────────┬─────────────┬─────────────┬──────────────┐
│ Package     │ Version     │ File        │ Type         │
├─────────────┼─────────────┼─────────────┼──────────────┤
│ requests    │ >=2.25.0    │ req.txt     │ Production   │
│ pytest      │ ^7.0.0      │ pyproj.toml │ Development  │
└─────────────┴─────────────┴─────────────┴──────────────┘
```

### JSON Format
```json
{
  "files": [
    {
      "file_path": "requirements.txt",
      "file_type": "requirements",
      "dependencies": [
        {
          "name": "requests",
          "version_spec": ">=2.25.0",
          "extras": [],
          "is_dev": false
        }
      ]
    }
  ]
}
```

## Logging

The scan command generates detailed logs with:
- Timestamp and analysis metadata
- Package usage summary across files
- Detailed per-file dependency breakdown
- Optional PyPI version information

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Documentation

- [Parser Documentation](dependency_reader/parsers/README.md)
- [Examples](docs/examples/)
- [Architecture Details](docs/)

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
1. Check the documentation
2. Search existing issues
3. Create a new issue with reproduction steps

---

**Built with ❤️ for Python developers who need comprehensive dependency analysis**