# Changelog

All notable changes to ModelBridge are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/).

## [1.0.0] - 2026-08-28

### Added

- Official CLI (`modelbridge`) with config, login, status, providers, models, chat, embeddings, analytics, requests, org, and benchmark commands
- Python SDK (`modelbridge-sdk`) with sync/async clients and streaming
- TypeScript SDK (`@modelbridge/sdk`) with chat, embeddings, streaming, and types
- Plugin architecture for trusted provider extensions via entry points
- Benchmark framework in CLI
- Example applications (python-chat, streaming-chat, rag-example)
- Documentation structure for getting started, guides, API, SDK, deployment
- GitHub community files (CODE_OF_CONDUCT, SUPPORT, issue/PR templates)
- Release automation workflow
- Semantic versioning strategy (`VERSION` file)

### Changed

- API version aligned to 1.0.0
- Production Docker image uses multi-stage non-root build

### Security

- CLI masks secrets in configuration output
- Plugin system loads only trusted entry-point plugins

[1.0.0]: https://github.com/suragms/modelbridge/releases/tag/v1.0.0
