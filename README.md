# YCloud — Distributed Cloud Storage

YCloud is a browser-based distributed object-storage application built around chunking, replication, integrity verification, versioning and file reconstruction.

## Online application

The `frontend/` application is designed for GitHub Pages with Supabase Auth, Postgres metadata and Supabase Storage. It provides:

- Secure email/password authentication
- 5 MB file chunking in the browser
- SHA-256 checksum generation and verification
- Two managed copies of every chunk
- Version history for uploaded files
- Verified browser-side reconstruction and download
- File search, sorting and grid/list views
- Account and password management
- Storage and service health views

## Architecture

```text
Browser
  ↓
5 MB chunks → SHA-256 → Replica A + Replica B
  ↓                         ↓
Postgres metadata       Supabase Storage
  ↓
Verified reconstruction → Download
```

Replica A and Replica B are two managed object copies inside Supabase Storage. They are logical application replicas rather than two independently hosted physical servers.

## Local distributed-node implementation

The original FastAPI/Docker implementation remains in `api/`, `storage-node/` and `docker-compose.yml` for local development and physical-node failure/recovery demonstrations.

```bash
docker compose up --build
```

## GitHub Pages

The included `.github/workflows/deploy-ycloud.yml` publishes only `frontend/` to GitHub Pages.
