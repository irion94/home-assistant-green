# ADR 004: 70% Test Coverage Minimum Requirement

## Status

**Accepted** - November 2024

## Context

Automated testing ensures code quality, prevents regressions, and gives confidence when making changes. However, pursuing 100% test coverage can be wasteful, testing trivial code and slowing development.

We need a balanced approach that ensures quality without excessive testing overhead.

### Alternatives Considered

1. **No Coverage Requirement**
   - Pros: No overhead, fast development
   - Cons: No quality guarantee, regressions likely, technical debt

2. **100% Coverage Requirement**
   - Pros: Maximum confidence
   - Cons: Wasteful, tests trivial code, slows development, diminishing returns

3. **50% Coverage**
   - Pros: Some confidence, minimal overhead
   - Cons: Too low for production use, many critical paths untested

4. **70% Coverage** ✅
   - Pros: Good balance, critical paths covered, reasonable effort
   - Cons: Some code untested (acceptable trade-off)

5. **80%+ Coverage**
   - Pros: High confidence
   - Cons: Diminishing returns, significant overhead for last 10-30%

## Decision

We will enforce a **minimum 70% test coverage** requirement for the root project, with the following guidelines:

### Coverage Requirements

```python
# pyproject.toml
[tool.coverage.report]
fail_under = 70  # Build fails if coverage < 70%
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

### What Must Be Tested

✅ **Critical Paths** (always test):
- Configuration validation logic
- Deployment scripts core functionality
- Custom component initialization
- API interactions
- Data transformations
- Security-sensitive code

✅ **Edge Cases** (test when applicable):
- Error handling
- Boundary conditions
- Invalid inputs
- Network failures

❌ **Acceptable to Skip** (can exclude):
- Trivial getters/setters
- `__repr__` and `__str__` methods
- Type stubs and protocols
- Defensive programming (raise NotImplementedError)
- Debug-only code

### Subproject Requirements

- **Root Project**: 70% minimum (enforced in CI)
- **ha-strava-coach**: Own coverage requirements (already has ~80%+)

## Implementation

### CI Enforcement

```yaml
# .github/workflows/ci.yml
- name: Run tests with coverage
  run: pytest --cov=config/custom_components --cov-report=xml

- name: Check coverage threshold
  run: coverage report --fail-under=70
```

### Coverage Reporting

- **HTML Reports**: Generated and uploaded as CI artifacts
- **Codecov Integration**: Tracks coverage over time
- **PR Comments**: Coverage changes visible in PRs (optional)

## Consequences

### Positive

✅ **Quality Assurance**: Critical code paths tested
✅ **Regression Prevention**: Tests catch breaking changes
✅ **Confidence**: Safe to refactor with test safety net
✅ **Documentation**: Tests serve as usage examples
✅ **Onboarding**: New contributors understand code via tests
✅ **Balanced**: Not wasteful, focuses on important code
✅ **CI Integration**: Automated enforcement prevents regressions

### Negative

❌ **Initial Effort**: Writing tests takes time
❌ **Maintenance**: Tests need updates when code changes
❌ **Not Perfect**: 30% of code may be untested
❌ **False Security**: Coverage ≠ quality (bad tests pass coverage)

### Mitigations

- **Pragmatic Testing**: Focus on critical paths first
- **Test Factories**: Reusable fixtures in `conftest.py` reduce overhead
- **Examples**: Comprehensive test suites as reference
- **Review**: Code review ensures test quality, not just coverage
- **Incremental**: Can improve coverage over time

## Test Strategy

### Test Pyramid

```
    /\
   /  \     E2E Tests (few)
  /____\
 /      \   Integration Tests (some)
/________\
/__________\ Unit Tests (many)
```

### Test Distribution

- **Unit Tests** (~70%): Fast, isolated, test individual functions
- **Integration Tests** (~25%): Test component interactions
- **E2E Tests** (~5%): Test full workflows (config validation, deployment)

### Test Categories

**Configuration Tests** (`test_config_validation.py`):
- YAML syntax validation
- Secret references
- File structure
- Security checks

**Integration Tests** (`test_integrations.py`):
- Custom component structure
- Manifest validation
- Deployment scripts

**Automation Tests** (`test_automations.py`):
- Schema validation
- Best practices
- Security scanning

## Evolution

Coverage requirements may evolve:

- **Increase to 80%**: If quality issues arise
- **Decrease to 60%**: If excessive test maintenance burden
- **Differentiate**: Different requirements for different components

## Metrics

Track over time:
- Coverage percentage trend
- Test execution time
- Number of tests
- Flaky test rate

## Related

- See: tests/conftest.py for test fixtures
- See: pyproject.toml for coverage configuration
- See: .github/workflows/ci.yml for CI enforcement
- See: CONTRIBUTING.md for testing guidelines
