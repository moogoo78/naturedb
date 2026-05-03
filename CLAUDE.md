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

Run tests with:
```
! pytest tests/
```

## Notes

- Remember to stage files with `git add` before committing
- Check `git status` to see what's staged
- Use `git diff` to review changes before committing
