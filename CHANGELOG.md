# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Version counter (`/version` endpoint, frontend footer, `VERSION` file).

## [0.1.0-beta] - 2026-08-26

### Added
- Go backend migration (replaces the previous Python backend).
- AI shopping assistant: describe products in natural language and Graby fills your cart.
- Coto Digital integration (auth, search, delivery address, cart adapter).
- OpenRouter model fallback for product planning.
- PostgreSQL job queue with `FOR UPDATE SKIP LOCKED`.
- SSE and WebSocket live status updates.
- Frontend theme toggle (light / dark / system).

### Fixed
- Export `Theme` type from `ThemeProvider` to fix the production build.
