# Dependency Reader Core Module

This directory contains the core functionality of the Python Dependency Reader tool. Each module is designed with a specific responsibility following clean architecture principles.

## Module Overview

### 📁 Core Files

- **`cli.py`** - Main command-line interface using Click framework
- **`models.py`** - Data structures and type definitions
- **`utils.py`** - Common utilities and helper functions

### 🔧 Analysis Modules

- **`conflict_detector.py`** - Version conflict detection across files
- **`python_scanner.py`** - AST-based Python source code analysis
- **`pypi_client.py`** - PyPI API integration with caching

### 📄 Parsers Directory

- **`parsers/`** - File format parsers for different dependency formats

## Module Details

### CLI Interface (`cli.py`)

The main entry point providing three primary commands:

```python
@cli.command()
def parse():    # Parse traditional dependency files
    
@cli.command() 
def scan():     # Analyze Python source files

@cli.command()
def info():     # Get PyPI package information
```

**Key Features:**
- Click-based argument parsing
- Colored output using colorlog
- Verbose logging options
- Progress indicators
- Error handling with context

### Data Models (`models.py`)

Type-safe dataclasses for structured data:

```python
@dataclass
class Dependency:
    name: str
    version_spec: Optional[SpecifierSet]
    extras: List[str]
    is_dev: bool

@dataclass
class DependencyFile:
    file_path: Path
    file_type: str
    dependencies: List[Dependency]

@dataclass
class ConflictReport:
    package_name: str
    version_conflicts: List[VersionConflict]
```

### Python Scanner (`python_scanner.py`)

Advanced AST-based analysis of Python source files:

**Capabilities:**
- Parse Python AST to extract import statements
- Filter standard library modules (Python 3.11+)
- Handle relative imports intelligently
- Recursive directory scanning with smart filtering
- Generate comprehensive dependency reports

**Example Usage:**
```python
scanner = PythonScanner()
dep_files = scanner.scan_directory(path, recursive=True)
package_usage = scanner.merge_dependencies_by_package(dep_files)
```

### Conflict Detector (`conflict_detector.py`)

Analyzes version conflicts across multiple dependency files:

**Features:**
- Cross-file dependency comparison
- Version specification analysis using packaging library
- Dev vs production dependency tracking
- Detailed conflict reporting with file locations

**Algorithm:**
1. Group dependencies by package name
2. Compare version specifications
3. Identify incompatible ranges
4. Generate structured conflict reports

### PyPI Client (`pypi_client.py`)

Robust PyPI API integration:

**Features:**
- Rate limiting (10 requests/second)
- Local filesystem caching
- HTTP session with retry logic
- Exponential backoff for failures
- Package information retrieval

**Cache Strategy:**
- Cache location: `~/.cache/dependency_reader/`
- TTL: 1 hour for package info
- Automatic cache invalidation
- Error response caching (short TTL)

## Error Handling

Each module implements comprehensive error handling:

### Graceful Degradation
- Optional dependencies handled with fallbacks
- Network errors don't crash the application
- Invalid files are logged and skipped
- Parsing errors are isolated per file

### Logging Strategy
- Structured logging with levels (DEBUG, INFO, WARNING, ERROR)
- Colored output for enhanced user experience
- Verbose mode for debugging
- Context-aware error messages

## Integration Points

### Parser Integration
```python
# Automatic parser selection based on file type
if file_path.name == "requirements.txt":
    parser = RequirementsParser()
elif file_path.name == "Pipfile":
    parser = PipfileParser()
elif file_path.name == "pyproject.toml":
    parser = PyprojectParser()
```

### Data Flow
1. **Input**: File paths or directory paths
2. **Parsing**: Format-specific parsing to `Dependency` objects
3. **Analysis**: Conflict detection and PyPI validation
4. **Output**: Formatted results (JSON, Table, Simple)

### Extension Points
- New parsers can be added to `parsers/` directory
- Output formatters can be extended in `utils.py`
- Additional analysis modules follow the same pattern

## Performance Considerations

### Optimization Strategies
- **Lazy Loading**: Parsers loaded only when needed
- **Concurrent Processing**: Multiple files processed in parallel
- **Caching**: PyPI responses cached locally
- **Smart Filtering**: Skip known non-dependency directories

### Memory Management
- Stream processing for large files
- Generator-based directory traversal
- Limited cache size with LRU eviction
- Garbage collection of temporary objects

## Testing Approach

### Unit Testing
- Mock external dependencies (PyPI API)
- Test each parser independently
- Validate data model constraints
- Error condition testing

### Integration Testing
- End-to-end command testing
- Real file parsing validation
- Cache behavior verification
- Cross-platform compatibility

## Configuration

### Environment Variables
```bash
DEPENDENCY_READER_CACHE_DIR=/custom/cache/path
DEPENDENCY_READER_LOG_LEVEL=DEBUG
PYPI_API_TIMEOUT=30
```

### Default Settings
- Cache TTL: 3600 seconds
- Rate limit: 10 requests/second
- Timeout: 10 seconds
- Max retries: 3

## Future Enhancements

### Planned Features
- Plugin system for custom parsers
- Configuration file support
- Database storage backend
- Web dashboard interface
- CI/CD integration hooks

### Architecture Improvements
- Async/await for PyPI requests
- Event-driven architecture
- Microservice decomposition
- GraphQL API layer

---

*Each module is designed to be independently testable and maintainable while providing clear interfaces for integration.*