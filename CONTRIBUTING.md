# Contributing Guidelines

Thank you for your interest in contributing to the Insurance Claims Processing project! We welcome all contributions, including bug reports, feature requests, documentation improvements, and code contributions.

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in the [issue tracker](https://github.com/sinha4ravi/adk-insurance-lab/issues).
2. If not, create a new issue with a clear title and description.
3. Include steps to reproduce the issue, expected behavior, and actual behavior.
4. Add any relevant logs or screenshots.

### Suggesting Enhancements

1. Check if the enhancement has already been suggested.
2. Create a new issue with a clear title and description of the enhancement.
3. Explain why this enhancement would be useful and how it should work.

### Making Code Changes

1. Fork the repository and create a new branch for your changes.
2. Make your changes following the coding standards.
3. Add or update tests as needed.
4. Update the documentation if necessary.
5. Run the test suite to ensure all tests pass.
6. Submit a pull request with a clear description of your changes.

## Development Setup

### Prerequisites

- Python 3.9+
- pip
- Git

### Installation

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/your-username/adk-insurance-lab.git
   cd adk-insurance-lab
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. Set up pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Coding Standards

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines
- Use type hints for all function signatures
- Write docstrings following [Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- Keep functions small and focused on a single responsibility
- Write meaningful commit messages following [Conventional Commits](https://www.conventionalcommits.org/)

### Testing

- Write tests for all new features and bug fixes
- Run the test suite before submitting a pull request:
  ```bash
  pytest
  ```
- Ensure test coverage remains high (minimum 80%)

## Pull Request Process

1. Update the README.md with details of changes if needed.
2. Increase the version number in any examples and the README.md if applicable.
3. The PR must pass all CI/CD checks.
4. The PR must be reviewed by at least one maintainer.
5. Once approved, a maintainer will merge the PR.

## Code Review Process

- All pull requests require at least one approval from a maintainer.
- Reviewers will check for:
  - Code quality and style
  - Test coverage
  - Documentation updates
  - Security implications
  - Performance considerations
- Be responsive to feedback and be prepared to make changes.

## Release Process

1. Create a release branch from main.
2. Update the version in `__version__.py`.
3. Update the CHANGELOG.md with the changes in this release.
4. Create a pull request for the release.
5. Once merged, create a GitHub release with the version tag.
6. The CI/CD pipeline will automatically publish the package.

## Getting Help

If you have questions about the contribution process or need help, please open an issue or reach out to the maintainers.
