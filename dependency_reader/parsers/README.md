# Dependency File Parsers

This directory contains specialized parsers for different Python dependency file formats. Each parser implements a common interface while handling the unique syntax and requirements of its specific format.

## Supported Formats

### 📄 Requirements.txt (`requirements.py`)

The most common Python dependency format used by pip.

**Supported Features:**
- Basic package specifications: `package==1.0.0`
- Version constraints: `package>=1.0,<2.0`
- URL-based dependencies: `git+https://github.com/user/repo.git`
- Local file paths: `-e ./local_package`
- Extras: `package[extra1,extra2]`
- Comments and empty lines
- Environment markers: `package; python_version >= "3.8"`

**Example:**
```txt
# Production dependencies
requests>=2.25.0
django>=4.0,<5.0
psycopg2-binary==2.9.5

# Development dependencies  
pytest>=7.0.0
black==22.12.0

# Optional dependencies
redis[hiredis]>=4.0.0
```

### 📄 Pipfile (`pipfile_parser.py`)

Modern dependency management format used by Pipenv.

**Supported Features:**
- Production and development dependency sections
- Version constraints with caret notation: `"^1.0.0"`
- Git repositories: `{"git": "https://github.com/user/repo.git"}`
- Local paths: `{"path": "./local_package"}`
- Extras specification
- Python version requirements

**Example:**
```toml
[packages]
requests = ">=2.25.0"
django = "^4.0"
redis = {extras = ["hiredis"], version = ">=4.0.0"}

[dev-packages]
pytest = "^7.0.0"
black = "==22.12.0"
```

### 📄 Pyproject.toml (`pyproject_parser.py`)

Modern Python packaging standard supporting multiple tools.

**Supported Build Systems:**
- **Poetry**: `[tool.poetry.dependencies]`
- **PDM**: `[project.dependencies]`
- **Flit**: `[project.dependencies]`
- **Setuptools**: `[project.dependencies]`

**Example (Poetry):**
```toml
[tool.poetry.dependencies]
python = "^3.8"
requests = "^2.25.0"
django = {version = "^4.0", optional = true}

[tool.poetry.group.dev.dependencies]
pytest = "^7.0.0"
black = "^22.0.0"
```

## Parser Architecture

### Common Interface

All parsers implement the same interface pattern:

```python
class BaseParser:
    def parse_file(self, file_path: Path) -> List[Dependency]:
        """Parse a dependency file and return list of dependencies"""
        
    def _extract_dependencies(self, content: dict) -> List[Dependency]:
        """Extract dependencies from parsed content"""
        
    def _parse_version_spec(self, version_str: str) -> SpecifierSet:
        """Parse version specification string"""
```

### Error Handling Strategy

Each parser implements robust error handling:

1. **File Access Errors**: Handle missing files gracefully
2. **Parse Errors**: Log syntax errors and continue processing
3. **Version Errors**: Validate version specifications
4. **Encoding Issues**: Handle different file encodings

### Dependency Classification

Dependencies are classified into categories:

- **Production**: Required for application runtime
- **Development**: Only needed for development/testing
- **Optional**: Extra dependencies for specific features

## Implementation Details

### Requirements Parser

**Parsing Strategy:**
1. Line-by-line processing
2. Comment and whitespace handling
3. URL detection and parsing
4. Environment marker evaluation
5. Version constraint normalization

**Special Cases:**
- Editable installs (`-e` flag)
- Index URLs (`--index-url`)
- Extra index URLs (`--extra-index-url`)
- Constraint files (`-c`)
- Requirements files (`-r`)

### Pipfile Parser

**Parsing Strategy:**
1. TOML format parsing
2. Section-based dependency extraction
3. Complex dependency object handling
4. Version constraint conversion

**Fallback Mechanism:**
If `pipfile` library is unavailable, uses manual TOML parsing with limited functionality.

### Pyproject Parser

**Multi-Tool Support:**
The parser automatically detects the build system and adapts parsing logic:

```python
def _detect_build_system(self, data: dict) -> str:
    """Detect which build system is being used"""
    if "tool" in data and "poetry" in data["tool"]:
        return "poetry"
    elif "project" in data:
        return "pep621"  # PDM, Flit, setuptools
    return "unknown"
```

**Dependency Location Mapping:**
- Poetry: `tool.poetry.dependencies`
- PEP 621: `project.dependencies` and `project.optional-dependencies`
- Dev dependencies: Tool-specific sections

## Version Specification Handling

### Supported Formats

All parsers normalize version specifications to packaging library format:

```python
# Input formats
">=1.0"          → SpecifierSet(">=1.0")
"^1.0.0"         → SpecifierSet(">=1.0.0,<2.0.0")  # Poetry/npm style
"~=1.0"          → SpecifierSet("~=1.0")          # Compatible release
"1.0.*"          → SpecifierSet(">=1.0.0,<1.1.0") # Wildcard
```

### Constraint Resolution

The parsers handle complex version constraints:

```python
# Multiple constraints
">=1.0,<2.0,!=1.5.0"

# Environment markers
"package>=1.0; python_version >= '3.8'"

# Platform-specific
"package>=1.0; sys_platform == 'win32'"
```

## Extension Guide

### Adding New Parsers

1. **Create Parser Class:**
```python
class NewFormatParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_file(self, file_path: Path) -> List[Dependency]:
        # Implementation
        pass
```

2. **Integrate with CLI:**
```python
# In cli.py
if file_path.suffix == ".newformat":
    parser = NewFormatParser()
```

3. **Add Tests:**
```python
def test_new_format_parser():
    parser = NewFormatParser()
    deps = parser.parse_file(Path("test.newformat"))
    assert len(deps) > 0
```

### Custom Version Handlers

For formats with unique version syntax:

```python
def _parse_custom_version(self, version_str: str) -> SpecifierSet:
    """Handle custom version format"""
    if version_str.startswith("@"):
        # Handle Git refs: @branch, @tag, @commit
        return None  # No version constraint for VCS refs
    return SpecifierSet(version_str)
```

## Testing Strategy

### Unit Tests

Each parser has comprehensive unit tests:

```python
def test_requirements_parser():
    content = """
    requests>=2.25.0
    django==4.0.0  # Web framework
    pytest>=7.0.0  # Development only
    """
    parser = RequirementsParser()
    deps = parser._parse_content(content)
    assert len(deps) == 3
    assert deps[0].name == "requests"
```

### Integration Tests

End-to-end tests with real dependency files:

```python
def test_parse_real_files():
    """Test parsing actual dependency files from popular projects"""
    test_files = [
        "test_data/django_requirements.txt",
        "test_data/fastapi_pyproject.toml",
        "test_data/requests_Pipfile"
    ]
    # Test each file
```

## Performance Optimization

### Caching Strategy

- **File Content**: Cache parsed content for repeated access
- **Version Specs**: Cache SpecifierSet objects
- **Regex Patterns**: Compile once, use multiple times

### Memory Management

- **Streaming**: Process large files line by line
- **Lazy Loading**: Load parsers only when needed
- **Cleanup**: Clear temporary objects after processing

## Troubleshooting

### Common Issues

1. **Encoding Problems:**
```python
# Solution: Explicit encoding specification
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()
```

2. **Version Parse Errors:**
```python
# Solution: Graceful degradation
try:
    spec = SpecifierSet(version_str)
except InvalidSpecifier:
    logger.warning(f"Invalid version spec: {version_str}")
    spec = None
```

3. **Missing Dependencies:**
```python
# Solution: Optional imports with fallbacks
try:
    import pipfile
except ImportError:
    logger.warning("pipfile library not available, using fallback")
    pipfile = None
```

---

*These parsers form the foundation of the dependency analysis system, providing reliable and extensible file format support.*