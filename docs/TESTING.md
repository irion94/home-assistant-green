# Testing Guide

**Last Updated**: 2025-12-01
**Phase**: Phase 2 - Testing Infrastructure (COMPLETE)

---

## Table of Contents

1. [Overview](#overview)
2. [Frontend Testing](#frontend-testing)
3. [Backend Testing](#backend-testing)
4. [Running Tests](#running-tests)
5. [CI/CD Pipeline](#cicd-pipeline)
6. [Coverage Requirements](#coverage-requirements)
7. [Best Practices](#best-practices)

---

## Overview

The Home Assistant AI Companion has comprehensive test coverage across both frontend (React Dashboard) and backend (AI Gateway) components.

**Testing Stack**:
- **Frontend**: Vitest + React Testing Library + jsdom
- **Backend**: pytest + pytest-asyncio + pytest-cov
- **CI/CD**: GitHub Actions with Codecov integration

**Coverage Targets**:
- Frontend: 60%+ (statements, functions, lines)
- Backend: 70%+ (statements, branches, functions)

---

## Frontend Testing

### Setup

Frontend tests use Vitest as the test runner and React Testing Library for component testing.

**Key Files**:
- `react-dashboard/vitest.config.ts` — Vitest configuration
- `react-dashboard/src/test/setup.ts` — Global test setup and mocks
- `react-dashboard/src/test/mocks/` — Mock services (MQTT, API)

### Running Frontend Tests

```bash
cd /home/irion94/home-assistant-green/react-dashboard

# Run all tests
npm run test

# Run with UI
npm run test:ui

# Run with coverage
npm run test:coverage

# Watch mode (re-run on file changes)
npm run test:watch
```

### Test Structure

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

describe('ComponentName', () => {
  it('should render correctly', () => {
    render(<ComponentName />)
    expect(screen.getByText('Expected Text')).toBeInTheDocument()
  })
})
```

### Mocking Services

**MQTT Service** (globally mocked in setup.ts):
```typescript
import { mqttService } from '@/services/mqttService'

// mqttService is automatically mocked in all tests
// Methods available: connect, disconnect, publish, setRoomId, etc.
```

**API Service** (import mock):
```typescript
import { mockApiService } from '@/test/mocks/apiService'

// Use in tests
mockApiService.sendConversation.mockResolvedValue({ response: 'OK' })
```

### Testing Zustand Stores

```typescript
import { renderHook, act } from '@testing-library/react'
import { useVoiceStore } from '@/stores/voiceStore'

it('should update state correctly', () => {
  const { result } = renderHook(() => useVoiceStore())

  act(() => {
    result.current.addMessage({
      id: '1',
      type: 'user',
      text: 'Test',
      timestamp: Date.now(),
    })
  })

  expect(result.current.messages).toHaveLength(1)
})
```

### Coverage Thresholds

Defined in `vitest.config.ts`:
```typescript
coverage: {
  thresholds: {
    statements: 60,
    branches: 55,
    functions: 60,
    lines: 60,
  },
}
```

---

## Backend Testing

### Setup

Backend tests use pytest with async support and FastAPI TestClient.

**Key Files**:
- `ai-gateway/tests/conftest.py` — Shared fixtures
- `ai-gateway/tests/routers/` — Router endpoint tests
- `ai-gateway/tests/services/` — Service layer tests
- `ai-gateway/tests/security/` — Security module tests

### Running Backend Tests

```bash
cd /home/irion94/home-assistant-green/ai-gateway

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term

# Run specific test file
pytest tests/routers/test_conversation.py

# Run specific test
pytest tests/routers/test_conversation.py::test_conversation_endpoint

# Verbose output
pytest -v

# Show print statements
pytest -s
```

### Test Structure

```python
import pytest
from fastapi.testclient import TestClient

def test_endpoint(client: TestClient):
    """Test description."""
    response = client.post("/endpoint", json={"key": "value"})

    assert response.status_code == 200
    data = response.json()
    assert "expected_field" in data
```

### Fixtures

**Available fixtures** (from `conftest.py`):
```python
@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)

@pytest.fixture
def mock_ha_states():
    """Mock Home Assistant states."""
    return [...]

@pytest.fixture
def mock_ha_client(mock_ha_states):
    """Mock HomeAssistantClient."""
    client = MagicMock()
    client.get_states = AsyncMock(return_value=mock_ha_states)
    return client

@pytest.fixture
def mock_mqtt_client():
    """Mock MQTT client."""
    client = MagicMock()
    client.publish = MagicMock()
    return client
```

### Testing Async Functions

```python
import pytest

@pytest.mark.asyncio
async def test_async_function(mock_ha_client):
    """Test async functionality."""
    from app.services.conversation_client import ConversationClient

    client = ConversationClient(ha_client=mock_ha_client)
    response = await client.chat("Test command")

    assert response is not None
    assert mock_ha_client.call_service.called
```

### Coverage Thresholds

Target: 70%+ coverage across:
- Statements
- Branches
- Functions
- Lines

Check coverage with:
```bash
pytest --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

---

## Running Tests

### Local Development

**Frontend** (from `react-dashboard/`):
```bash
npm run test:watch  # Best for development
```

**Backend** (from `ai-gateway/`):
```bash
pytest --cov=app --cov-report=term  # With coverage
pytest -k "test_name"  # Run specific tests
```

### Before Committing

**Run both test suites**:
```bash
# Frontend
cd react-dashboard && npm run test:coverage

# Backend
cd ../ai-gateway && pytest --cov=app --cov-report=term

# Check coverage meets thresholds
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

File: `.github/workflows/test.yml`

**Triggers**:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

**Jobs**:
1. **test-backend**: Runs pytest with coverage, uploads to Codecov
2. **test-frontend**: Runs Vitest with coverage, uploads to Codecov
3. **coverage-check**: Validates coverage thresholds met

### Codecov Integration

Coverage reports are uploaded to Codecov for tracking:
- **Backend coverage**: `ai-gateway/coverage.xml`
- **Frontend coverage**: `react-dashboard/coverage/lcov.info`

**Flags**:
- `backend` — Backend test coverage
- `frontend` — Frontend test coverage

---

## Coverage Requirements

### Frontend (60%+ target)

**Critical paths** (must have tests):
- `voiceStore` (Zustand state management) — ✅ 5 tests
- `VoiceOverlay` component — ✅ 3 tests
- `ToolPanelSlider` component — ⏳ TODO
- `mqttService` integration — ✅ Mocked globally

**Current coverage**:
```bash
cd react-dashboard
npm run test:coverage
```

### Backend (70%+ target)

**Critical paths** (must have tests):
- `/conversation` endpoint — ✅ 2 tests
- Security modules (SecretsManager, URLValidator) — ✅ 35 tests
- LLM tools — ⏳ Phase 3
- Intent matcher — ✅ Existing tests

**Current coverage**:
```bash
cd ai-gateway
pytest --cov=app --cov-report=term
```

---

## Best Practices

### Frontend Testing

1. **Use semantic queries**: Prefer `getByRole`, `getByLabelText` over `getByTestId`
2. **Mock at boundaries**: Mock services (MQTT, API), not implementation details
3. **Test user behavior**: Simulate clicks, inputs, not internal state changes
4. **Keep tests focused**: One assertion per test when possible
5. **Use `act()` for state updates**: Wrap store mutations in `act()`

**Example**:
```typescript
it('should handle user click', async () => {
  const user = userEvent.setup()
  render(<Button onClick={mockFn}>Click me</Button>)

  await user.click(screen.getByRole('button', { name: /click me/i }))

  expect(mockFn).toHaveBeenCalledOnce()
})
```

### Backend Testing

1. **Use fixtures**: Leverage `conftest.py` for reusable test data
2. **Mock external services**: Don't call real Home Assistant or Ollama
3. **Test error paths**: Include negative test cases
4. **Mark async tests**: Use `@pytest.mark.asyncio` for async functions
5. **Verify side effects**: Check that mocks were called correctly

**Example**:
```python
def test_error_handling(client: TestClient):
    """Test error response."""
    response = client.post("/endpoint", json={"invalid": "data"})

    assert response.status_code == 400
    assert "error" in response.json()
```

### Code Coverage

1. **Aim for meaningful coverage**: 60-70% is target, not 100%
2. **Focus on critical paths**: User flows, data transformations, error handling
3. **Don't test implementation**: Test behavior, not internals
4. **Exclude generated code**: Test setup, mocks, types don't need coverage
5. **Review coverage reports**: Identify untested critical code

---

## Troubleshooting

### Frontend Tests Fail with "scrollIntoView is not a function"

Already fixed in `src/test/setup.ts`:
```typescript
Element.prototype.scrollIntoView = vi.fn()
```

### Backend Tests Fail with "No module named 'app'"

Run from `ai-gateway/` directory, not repository root.

### MQTT/API Service Not Mocked

Check that `setup.ts` is loaded (configured in `vitest.config.ts`):
```typescript
test: {
  setupFiles: ['./src/test/setup.ts'],
}
```

### Async Test Timeout

Increase timeout in pytest:
```python
@pytest.mark.asyncio
@pytest.mark.timeout(10)  # 10 second timeout
async def test_slow_operation():
    ...
```

---

## Next Steps

### Phase 3: Tool Testing & Registry

After Phase 2 completion, proceed to [Phase 3: Tool Testing & Registry](/.claude/plans/phase-03-tool-testing.md) for:
- 100% coverage of 8 tools
- PanelRegistry tests
- Learning systems tests

---

## References

- **Frontend Tests**: `react-dashboard/src/**/__tests__/`
- **Backend Tests**: `ai-gateway/tests/`
- **CI/CD Workflow**: `.github/workflows/test.yml`
- **Phase 2 Plan**: `/.claude/plans/phase-02-testing.md`

---

**For questions or issues, refer to the Phase 2 implementation plan or CLAUDE.md troubleshooting section.**
