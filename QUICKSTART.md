
# 🚀 Quick Start Guide

Get up and running with Python Dependency Reader in under 5 minutes!

## 📦 What is Python Dependency Reader?

A comprehensive CLI tool that analyzes Python dependencies across multiple file formats with advanced security and license checking capabilities.

**Key Features:**
- 🔍 Multi-format support (requirements.txt, Pipfile, pyproject.toml, Python source)
- 🛡️ Security vulnerability detection 
- 📜 License compatibility analysis
- ⚡ High-performance analysis (~1000 files/second)
- 📊 Rich output formats (Table, JSON, HTML)

## ⚡ Quick Commands

### 1. Get Help
```bash
python main.py --help
```

### 2. Analyze Current Directory
```bash
# Basic analysis
python main.py parse

# Comprehensive analysis with security and license checking
python main.py analyze --check-security --check-licenses
```

### 3. Check Specific Package Security
```bash
python main.py info django --check-security --check-license
```

### 4. Scan Python Source Files
```bash
python main.py scan --path ./src --recursive
```

### 5. Generate HTML Report
```bash
python main.py analyze --format html --output report.html
```

## 🎯 Common Use Cases

### Security Audit
```bash
# Find all security vulnerabilities
python main.py security --severity high

# Check specific directory for vulnerabilities  
python main.py analyze --path ./production --check-security
```

### License Compliance
```bash
# Check license compatibility
python main.py licenses --check-compatibility

# Generate compliance report
python main.py analyze --check-licenses --format html --output compliance.html
```

### CI/CD Integration
```bash
# JSON output for automation
python main.py analyze --check-security --format json > security_report.json

# Exit with error if high-severity vulnerabilities found
python main.py security --severity high --format simple | grep "HIGH\|CRITICAL" && exit 1
```

### Development Workflow
```bash
# Check new feature branch
python main.py scan --path ./new_feature --recursive

# Find version conflicts across files
python main.py parse --detect-conflicts

# Validate dependencies against PyPI
python main.py parse --check-pypi
```

## 📊 Output Formats

### Table (Default)
Human-readable with color coding and status indicators

### JSON
Machine-readable for automation and integration
```bash
python main.py analyze --format json
```

### HTML
Interactive reports with graphs and dashboards
```bash
python main.py analyze --format html --output report.html
```

### Simple
Clean text output perfect for CI/CD logs
```bash
python main.py analyze --format simple
```

## 🛠️ Advanced Options

### Security Analysis
```bash
# Filter by severity
python main.py security --severity medium

# Check specific path
python main.py security --path ./critical_code
```

### Performance Options
```bash
# Recursive scanning
python main.py scan --recursive

# Save to custom log
python main.py scan --log dependencies.log

# Multiple output formats
python main.py analyze --format table --output analysis.txt
```

## 🔧 Configuration

### Environment Variables
```bash
# Cache configuration
export DEPENDENCY_READER_CACHE_TTL=7200
export PYPI_RATE_LIMIT=10

# Logging
export DEPENDENCY_READER_LOG_LEVEL=DEBUG
```

### Verbose Output
```bash
python main.py -v analyze  # Detailed logging
```

## 🎪 Try the Demo

Run the comprehensive demo to see all features:
```bash
python demo.py
```

## 📚 Next Steps

1. **Read the full documentation**: [docs/README.md](docs/README.md)
2. **Check the examples**: [examples/](examples/)  
3. **Run performance benchmarks**: `python -m pytest tests/performance/ --benchmark`
4. **Explore the architecture**: [Architecture diagram](docs/images/architecture.svg)

## ❓ Need Help?

- Check the comprehensive [README.md](README.md)
- Browse [usage examples](docs/examples/README.md)
- Run `python main.py COMMAND --help` for command-specific help
- Review [CHANGELOG.md](CHANGELOG.md) for version details

---

**Happy analyzing! 🐍✨**
