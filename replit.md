# Overview

Python Dependency Reader is a comprehensive CLI tool that reads, parses, and analyzes multiple dependency file formats commonly used in Python projects. The tool supports requirements.txt, Pipfile, and pyproject.toml files, providing unified dependency analysis with conflict detection capabilities and PyPI integration for package validation. Additionally, it includes a powerful Python source code scanner that uses AST analysis to extract dependencies from import statements. The tool can search for dependency files both in a specific directory and recursively through subdirectories, making it suitable for complex multi-module projects.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Components

### Parser Architecture
The application uses a modular parser system with separate parsers for each dependency file format:
- **RequirementsParser**: Handles requirements.txt files with support for various pip options and URL-based dependencies
- **PipfileParser**: Processes Pipfile format with fallback to manual parsing if the pipfile library is unavailable
- **PyprojectParser**: Supports multiple pyproject.toml formats including Poetry, PDM, and Flit
- **PythonScanner**: Uses AST analysis to extract dependencies from Python import statements with stdlib filtering

### Data Models
The system uses dataclasses for type-safe data representation:
- **Dependency**: Represents individual packages with version specifications, extras, and dev/production classification
- **DependencyFile**: Groups dependencies by their source file with metadata
- **ConflictReport**: Structures conflict detection results for cross-file analysis

### Conflict Detection
The ConflictDetector analyzes dependencies across multiple files to identify version conflicts, grouping packages by name and comparing version specifications using packaging library standards.

### CLI Interface
Built with Click framework providing three main commands:
- **parse**: Traditional dependency file analysis (requirements.txt, Pipfile, pyproject.toml)
- **scan**: Python source code analysis with AST-based import extraction
- **info**: Direct PyPI package information lookup

Features include:
- Command-line argument parsing with support for recursive directory searching
- Colored output using colorlog
- Verbose logging options
- Structured command groups for extensibility
- Flexible path specification with recursive search capabilities
- Custom log file output with detailed dependency analysis

### Caching and Rate Limiting
PyPI client implements intelligent caching and rate limiting:
- Local filesystem cache for API responses
- HTTP session with retry strategies
- Configurable rate limiting to respect PyPI API limits

## Design Patterns

### Strategy Pattern
Different parsers implement a common interface, allowing the system to handle various file formats uniformly without tight coupling.

### Factory Pattern
Parser selection based on file type detection, enabling easy addition of new dependency file formats.

### Repository Pattern
PyPI client abstracts external API interactions with built-in caching and error handling.

## Error Handling
Graceful degradation when optional dependencies are missing, with fallback parsing strategies and comprehensive logging for debugging.

# External Dependencies

## Core Libraries
- **click**: Command-line interface framework for argument parsing and command structure
- **colorlog**: Colored logging output for enhanced user experience
- **packaging**: Python packaging utilities for version specification parsing and validation
- **requests**: HTTP client for PyPI API interactions with retry capabilities

## Optional Dependencies
- **pipfile**: For native Pipfile parsing (with manual fallback)
- **toml**: Required for pyproject.toml file parsing
- **urllib3**: Enhanced HTTP retry mechanisms through requests

## External Services
- **PyPI API**: Package information retrieval and validation at https://pypi.org/pypi
- **Local Filesystem**: Caching system using user's home directory cache folder

## Development Tools
- **logging**: Built-in Python logging with colored output formatting
- **pathlib**: Modern file path handling
- **dataclasses**: Type-safe data structure definitions