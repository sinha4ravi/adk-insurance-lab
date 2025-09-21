# Development Guide

## Prerequisites

- Python 3.9+
- pip 20.0.0+
- Git
- Docker (optional, for containerized development)

## Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/sinha4ravi/adk-insurance-lab.git
   cd adk-insurance-lab
   ```

2. **Set up a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your local configuration
   ```

## Project Structure

```
.
├── insurance_agent/           # Main package
│   ├── __init__.py
│   ├── main.py               # Application entry point
│   ├── config.py             # Configuration management
│   ├── models/               # Data models
│   ├── services/             # Business logic
│   └── subagents/            # Specialized agent implementations
├── tests/                    # Test suite
├── docs/                     # Documentation
├── scripts/                  # Utility scripts
├── .env.example              # Example environment variables
├── requirements.txt          # Production dependencies
├── requirements-dev.txt      # Development dependencies
└── README.md                 # Project documentation
```

## Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=insurance_agent

# Run a specific test file
pytest tests/test_agent.py
```

## Code Style

This project uses:
- Black for code formatting
- isort for import sorting
- flake8 for linting

```bash
# Format code
black .

# Sort imports
isort .

# Check code style
flake8
```

## Git Workflow

1. Create a new branch for your feature or bugfix
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them with a descriptive message
   ```bash
   git add .
   git commit -m "Add new feature for processing claims"
   ```

3. Push your changes and create a pull request
   ```bash
   git push origin feature/your-feature-name
   ```

## Debugging

```bash
# Run with debug logging
LOG_LEVEL=DEBUG python -m insurance_agent.main

# Start a debugger at point of failure
pytest --pdb
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
