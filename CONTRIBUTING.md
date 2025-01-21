# Contributing to Gurubase

We love your input! We want to make contributing to Gurubase as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

1. Fork the repo and create your branch from `master`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Development Setup

We use VSCode devcontainers for development. This ensures a consistent development environment for all contributors.

### Frontend (Next.js)

```bash
cd src/gurubase-frontend

# Install dependencies
yarn install

# Run in development mode
yarn dev-selfhosted
```

### Backend (Django)

The backend development environment is configured using VSCode devcontainers. To get started:

1. Install VSCode and the "Remote - Containers" extension
2. Open the project in VSCode
3. When prompted, click "Reopen in Container" or run the "Remote-Containers: Reopen in Container" command
4. The container will be built and configured automatically

Once inside the container:

```bash
cd src/gurubase-backend/backend

bash migrate_runserver.sh
```

## Pull Request Process

1. Update the README.md with details of changes to the interface, if applicable.
2. Update the CHANGELOG.md with a note describing your changes.
3. The PR will be merged once you have the sign-off of at least one other developer.

## Code Style

### Frontend

- Use ESLint and Prettier configurations provided in the project
- Follow React best practices and hooks guidelines
- Use functional components
- Implement proper TypeScript types
- Follow the existing component structure

### Backend

- Follow PEP 8 style guide
- Use Django's coding style
- Write docstrings for all functions and classes
- Keep functions small and focused
- Use type hints where possible

## Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

## License

By contributing, you agree that your contributions will be licensed under its Apache License 2.0. 