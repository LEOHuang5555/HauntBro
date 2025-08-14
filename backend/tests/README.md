# FastAPI Backend Test Suite

## Overview

This comprehensive test suite provides full coverage for the HauntBro FastAPI backend application using pytest with async database testing.

## Test Structure

```
backend/tests/
├── README.md              # This file
├── conftest.py            # Test configuration and fixtures
├── pytest.ini            # Pytest configuration (in project root)
├── run_tests.py           # Test runner script
├── api/                   # API endpoint tests
│   ├── test_auth.py       # Authentication API tests
│   ├── test_search.py     # Search API tests
│   ├── test_content.py    # Content management API tests
│   └── test_admin.py      # Admin API tests
├── integration/           # Integration tests
│   └── test_full_workflow.py  # End-to-end workflow tests
└── unit/                  # Unit tests
    └── test_security.py   # Security service unit tests
```

## Test Coverage

### API Tests (`api/`)

- **Authentication API** (`test_auth.py`): 20+ tests covering registration, login, token management, profile updates, and password changes
- **Search API** (`test_search.py`): 15+ tests covering semantic search, filters, suggestions, and trending queries
- **Content Management API** (`test_content.py`): 15+ tests covering story details, favorites, ratings, and reading history
- **Admin API** (`test_admin.py`): 15+ tests covering system statistics, user management, and content moderation

### Integration Tests (`integration/`)

- **Full Workflow Tests** (`test_full_workflow.py`): End-to-end user journeys from registration to content interaction
- **Data Consistency Tests**: Verifying data integrity across API calls
- **Authentication Flow Tests**: Complete authentication workflows
- **Concurrent Operations Tests**: Testing race conditions and concurrent user actions

### Unit Tests (`unit/`)

- **Security Service Tests** (`test_security.py`): 13+ tests covering JWT token management, password hashing, and security utilities

## Test Features

### Fixtures and Mocks

- **Database Fixtures**: In-memory SQLite database for testing
- **User Fixtures**: Pre-configured test users (regular and admin)
- **Authentication Fixtures**: JWT tokens for authenticated requests
- **Mock Services**: Redis, embedding manager, and other external services

### Test Categories

Tests are organized with pytest markers:

- `@pytest.mark.unit`: Unit tests for individual components
- `@pytest.mark.integration`: Integration tests for workflows
- `@pytest.mark.api`: API endpoint tests
- `@pytest.mark.auth`: Authentication-related tests
- `@pytest.mark.admin`: Admin functionality tests
- `@pytest.mark.slow`: Performance and load tests

## Running Tests

### Using the Test Runner

```bash
# Run all tests
python backend/tests/run_tests.py

# Run specific test types
python backend/tests/run_tests.py --type unit
python backend/tests/run_tests.py --type integration
python backend/tests/run_tests.py --type api
python backend/tests/run_tests.py --type auth
python backend/tests/run_tests.py --type admin

# Run with coverage
python backend/tests/run_tests.py --coverage

# Run with verbose output
python backend/tests/run_tests.py --verbose
```

### Using pytest directly

```bash
# Run all tests
pytest backend/tests/

# Run specific test files
pytest backend/tests/unit/test_security.py
pytest backend/tests/api/test_auth.py

# Run with markers
pytest -m "unit" backend/tests/
pytest -m "auth" backend/tests/
pytest -m "not slow" backend/tests/

# Run with coverage
pytest --cov=backend/app backend/tests/
```

## Test Configuration

### Environment Variables

Tests use these environment variables:

```bash
TESTING=true
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hauntbro_test
DB_USER=test_user
DB_PASSWORD=test_password
JWT_SECRET_KEY=test_secret_key_for_testing_only
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Database Setup

Tests use SQLite in-memory databases for fast, isolated testing:

- Each test function gets a fresh database
- Tables are created automatically from SQLAlchemy models
- No cleanup required between tests

### Async Testing

All tests support async/await patterns:

- Fixtures are async-compatible
- HTTP client uses `httpx.AsyncClient`
- Database operations use async SQLAlchemy patterns

## Test Examples

### Basic API Test

```python
async def test_user_registration(client: AsyncClient):
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    }
    
    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["username"] == user_data["username"]
```

### Authenticated API Test

```python
async def test_get_favorites(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/content/favorites", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "favorites" in data
    assert "pagination" in data
```

### Database Fixture Test

```python
async def test_user_creation(test_db, test_user):
    assert test_user.username == "testuser"
    assert test_user.is_active is True
    
    # User is already in the database
    user = test_db.query(User).filter_by(username="testuser").first()
    assert user is not None
```

## Performance Considerations

- **Fast Execution**: Unit tests run in <3 seconds
- **Parallel Testing**: Tests can be run with `pytest-xdist`
- **Memory Usage**: In-memory databases minimize resource usage
- **Isolation**: Each test is completely isolated

## Continuous Integration

The test suite is designed for CI/CD pipelines:

- Exit codes indicate test success/failure
- Supports parallel execution
- Generates coverage reports
- Compatible with GitHub Actions, Jenkins, etc.

## Test Metrics

Current test coverage includes:

- **65+ total tests** across all categories
- **API endpoints**: 100% coverage of implemented endpoints
- **Authentication flows**: Complete registration to logout workflows
- **Error handling**: Invalid inputs, unauthorized access, not found scenarios
- **Data validation**: Pydantic schema validation testing
- **Security**: JWT token management, password hashing, permission checks

## Adding New Tests

### New API Endpoint Test

1. Add test function to appropriate file in `api/`
2. Use existing fixtures (`client`, `auth_headers`, etc.)
3. Follow naming convention: `test_endpoint_scenario`
4. Add appropriate pytest markers

### New Integration Test

1. Add test to `integration/test_full_workflow.py`
2. Create complete user journeys
3. Test data consistency across multiple API calls
4. Use `@pytest.mark.integration` marker

### New Unit Test

1. Create new file in `unit/` directory
2. Test individual components in isolation
3. Mock external dependencies
4. Use `@pytest.mark.unit` marker

## Best Practices

- **Test Names**: Descriptive names explaining what is being tested
- **Test Structure**: Arrange-Act-Assert pattern
- **Fixtures**: Reuse common setup through fixtures
- **Assertions**: Clear, specific assertions
- **Error Cases**: Test both success and failure scenarios
- **Documentation**: Comment complex test logic

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure project root is in Python path
2. **Database Errors**: Check SQLAlchemy model definitions
3. **Authentication Errors**: Verify JWT configuration
4. **Async Errors**: Use `await` for async operations

### Debug Tips

```bash
# Run single test with output
pytest -s backend/tests/unit/test_security.py::TestSecurityService::test_password_hashing

# Run with debugging
pytest --pdb backend/tests/api/test_auth.py

# Show local variables on failure
pytest --tb=long backend/tests/
```

This test suite provides comprehensive coverage of the FastAPI backend, ensuring reliability, security, and maintainability of the HauntBro application.