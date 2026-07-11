# RDG Bot Development Guidelines

## Testing Requirements

**All new code MUST include tests BEFORE being committed or deployed.**

### When to write tests:
- ✅ Any new feature or handler
- ✅ Any bug fix
- ✅ Any service method change
- ✅ Any change to database persistence logic
- ✅ Changes to core business logic

### Test-Driven Development (TDD) preferred:
1. Write tests first (RED phase)
2. Implement the feature (GREEN phase)
3. Refactor if needed (REFACTOR phase)
4. Commit only when all tests pass

### Current test coverage:
- 71+ tests across service and handler layers
- All tests must pass before committing
- Use `pytest tests/ -v` to verify locally before pushing

### Test organization:
- **test_services.py**: Service layer tests (business logic)
- **test_handlers.py**: Handler tests (Telegram interactions)
- Tests use in-memory SQLite database for speed
- Each test class groups related functionality

## Database

### Persistence guarantee:
- Always use `flush()` before `commit()` for ORM updates
- This ensures all pending changes are written to the database
- Critical for PostgreSQL (Railway) compatibility

Example:
```python
recipe.external_status = "defined"
self.session.flush()  # Ensure update is persisted
self.session.commit()
```

## Code Style

- Simple, readable code over clever code
- Minimal error handling (only at system boundaries)
- Comments only where logic isn't self-evident
- No premature abstractions

## Git Workflow

### Before committing:
1. All tests pass locally
2. Code is tested and working
3. Commit message references the why, not the what

### Commit format:
```
Brief summary of change

Longer explanation if needed, including:
- What was changed and why
- Any bug fixes or features
- Test coverage added

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
```

## Deployment

- Push only when all tests pass
- Railway auto-deploys on main branch push
- Test with `/dbstatus` command to verify database state
