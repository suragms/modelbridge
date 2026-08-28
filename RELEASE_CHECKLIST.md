# Release Checklist

Before tagging a release:

- [ ] All tests passing (`apps/api`, CLI, Python SDK)
- [ ] Frontend build succeeds
- [ ] Security review completed
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] VERSION file bumped (SemVer)
- [ ] Package versions synced (CLI, SDKs, API, web)
- [ ] Docker build verified locally
- [ ] Database migrations tested (`alembic upgrade head`)
- [ ] Upgrade path documented
- [ ] LICENSE file present
- [ ] No secrets in repository
- [ ] Release notes drafted

After tagging `vX.Y.Z`:

- [ ] GitHub Release created with notes
- [ ] Docker images tagged (if publishing)
- [ ] PyPI/npm publish (only if configured — not automatic by default)
