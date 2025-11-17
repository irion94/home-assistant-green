# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) that document significant architectural and design decisions made in this project.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision made along with its context and consequences.

## Format

Each ADR follows this structure:

- **Title**: Short, descriptive name
- **Status**: Proposed, Accepted, Deprecated, Superseded
- **Context**: The issue motivating this decision
- **Decision**: The change we're proposing/making
- **Consequences**: Positive and negative outcomes

## ADR Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](001-tailscale-deployment.md) | Use Tailscale for Secure Deployment | Accepted | 2024-11 |
| [002](002-packages-pattern.md) | Modular Configuration with Packages Pattern | Accepted | 2024-11 |
| [003](003-git-based-deployment.md) | Git-Based Configuration Management | Accepted | 2024-11 |
| [004](004-test-coverage-requirements.md) | 70% Test Coverage Minimum | Accepted | 2024-11 |

## Creating a New ADR

When making a significant architectural decision:

1. Copy the template: `cp docs/adr/000-template.md docs/adr/XXX-decision-name.md`
2. Fill in the sections
3. Submit as part of your PR
4. Update this index

## Significant Decisions

Decisions worth documenting include:

- Technology choices (frameworks, libraries, tools)
- Architectural patterns
- Deployment strategies
- Security approaches
- Data management strategies
- Testing strategies
- CI/CD pipeline design

## Reference

Based on [Michael Nygard's ADR format](http://thinkrelevance.com/blog/2011/11/15/documenting-architecture-decisions).
