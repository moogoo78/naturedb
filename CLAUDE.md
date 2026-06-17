# Claude Code Configuration for NatureDB

## Git Workflow

### Quick Commit
Use this to commit with a message:

```
! git commit -m "your message here"
```

Or run `! git commit` to open your editor for the message.

### Full Workflow
For a complete commit flow with staging:

```
! git add .
! git commit -m "message"
! git status
```

## Development

- **Main branch**: `devel`
- **Git user**: moogoo
- **Email**: moogoo78@gmail.com

## Testing

There is no local Python/pytest — tests run inside the `flask` container.
Make sure it is up first: `docker compose up -d flask`.

Run the full suite:
```
! docker compose exec flask bash -c "cd /code && python -m pytest tests/"
```

Run a single file / class / test:
```
! docker compose exec flask bash -c "cd /code && python -m pytest tests/test_api.py"
! docker compose exec flask bash -c "cd /code && python -m pytest tests/test_api.py::TestPublicSpecimensEndpoint -v"
```

Notes:
- New pip packages must be installed in the container before tests can import
  them: `docker compose exec flask pip install <pkg>`.
- `test_api.py` carries some pre-existing, unrelated failures (e.g. a missing
  `mask_coordinates` import, CORS assertions on legacy `/api/v1` endpoints) —
  these are not regressions.

## Notes

- Remember to stage files with `git add` before committing
- Check `git status` to see what's staged
- Use `git diff` to review changes before committing
