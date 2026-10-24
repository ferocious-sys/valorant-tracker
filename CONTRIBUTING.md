
# Contributing to Valorant Tracker

Thank you for your interest in contributing to Valorant Tracker! Contributions such as bug fixes, feature improvements, documentation updates, and usability enhancements are welcome.

## Table of Contents

- [Getting Started](#getting-started)
- [Finding Something to Work On](#finding-something-to-work-on)
- [Development Guidelines](#development-guidelines)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)
- [Submitting Changes](#submitting-changes)
- [Pull Request Checklist](#pull-request-checklist)
- [Code of Conduct](#code-of-conduct)

## Getting Started

1. Read the project README to understand its purpose, features, and setup instructions.
2. Check existing issues and pull requests to avoid duplicating work.
3. Fork this repository on GitHub.
4. Clone your fork to your local machine.
5. Follow the installation and development instructions documented in the project.
6. Create a separate branch for your changes.

Example:

```bash
git clone https://github.com/YOUR-USERNAME/valorant-tracker.git
cd valorant-tracker
git checkout -b feature/your-feature-name
```

Replace `YOUR-USERNAME` with your GitHub username.

Use the project's existing development tools and instructions. Do not assume a particular package manager or runtime unless specified by the project.

## Finding Something to Work On

You can contribute by:

- Fixing reproducible bugs.
- Improving the user interface and accessibility.
- Adding useful tracker features.
- Improving performance and reliability.
- Updating documentation and setup instructions.
- Adding or improving automated tests.
- Improving error handling and user feedback.

For substantial changes, open an issue first to discuss your proposal with the maintainer.

## Development Guidelines

Please follow these guidelines:

- Keep changes focused and easy to review.
- Follow the existing code style and project architecture.
- Use clear, descriptive names for variables, functions, and components.
- Add or update tests when appropriate.
- Update documentation when behavior or setup instructions change.
- Avoid introducing unnecessary dependencies.
- Never commit API keys, access tokens, passwords, or other secrets.
- Do not commit personal data, private account information, or unnecessary generated files.
- Do not claim that a feature works unless it has been tested appropriately.

Valorant Tracker should use authorized data sources and comply with applicable game, platform, and API terms. Do not introduce features that bypass security controls, access private accounts without authorization, or automate prohibited gameplay.

## Reporting Bugs

Before opening a bug report:

1. Search existing issues for the same problem.
2. Confirm that you can reproduce the issue when possible.
3. Record the relevant environment details.
4. Remove passwords, tokens, personal information, and other sensitive data from logs and screenshots.

Use the Bug Report issue template when available.

## Suggesting Features

Feature suggestions should explain:

- The problem the feature would solve.
- The proposed behavior.
- Why it would benefit users.
- Any relevant examples or mockups.

Use the Feature Request issue template when available.

## Submitting Changes

1. Create a branch for your changes.
2. Make your changes in small, logical commits.
3. Run the relevant tests, checks, or build commands documented by the project.
4. Review your changes for accidental secrets or unrelated files.
5. Push your branch to your fork.
6. Open a pull request against the original repository's default branch.
7. Complete the pull request template and explain what changed and how you tested it.

Example:

```bash
git add .
git commit -m "Describe your changes"
git push origin feature/your-feature-name
```

Only stage the files you intend to include in the contribution.

## Pull Request Checklist

Before submitting your pull request, make sure:

- [ ] The change has a clear purpose.
- [ ] The code follows the project's existing conventions.
- [ ] Relevant tests or checks have been run.
- [ ] Documentation has been updated if needed.
- [ ] No secrets or private information are included.
- [ ] The pull request description explains the change.
- [ ] Any relevant issues are linked.

The maintainer may request revisions before merging a contribution.

## Code of Conduct

Be respectful, constructive, and welcoming to other contributors.

Harassment, discrimination, personal attacks, and intentionally disruptive behavior are not acceptable.

## Questions

For project questions, use GitHub Issues or Discussions if they are enabled and appropriate for your question.

For security vulnerabilities, follow the instructions in [SECURITY.md](SECURITY.md) instead of posting sensitive details publicly.

Thank you for helping improve Valorant Tracker!
