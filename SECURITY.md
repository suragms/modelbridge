# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in ModelBridge, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email security@modelbridge.dev with:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Security Measures

ModelBridge implements the following security measures:

### Authentication
- JWT-based authentication with configurable expiration
- API key authentication with SHA-256 hashing
- Password hashing with bcrypt

### Data Protection
- Provider API keys are encrypted at rest using Fernet symmetric encryption
- No plaintext storage of secrets
- No prompt/response logging by default

### API Security
- CORS configuration
- Request size limits
- Rate limiting (configurable per API key/user)
- Input validation on all endpoints
- No exposure of internal stack traces in production

### Infrastructure
- Docker security best practices
- Environment-based configuration
- No secrets committed to repository

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x | ✅ |

## Security Best Practices for Deployment

1. Generate strong, unique values for `JWT_SECRET` and `ENCRYPTION_KEY`
2. Use HTTPS in production
3. Restrict CORS origins to your domain
4. Enable rate limiting
5. Use a reverse proxy (nginx, Traefik)
6. Keep dependencies updated
7. Use environment variables for all secrets
8. Run containers as non-root users
