# YCloud Architecture

## Browser layer

The frontend authenticates with Supabase Auth and performs chunking, checksum calculation, concurrent upload, integrity verification and file reconstruction in the browser.

## Metadata layer

Postgres stores:

- `files` — logical files owned by authenticated users
- `versions` — immutable upload versions and status
- `chunks` — chunk order, size, SHA-256 checksum and replica paths

Row Level Security limits records to the authenticated owner.

## Object layer

Every chunk is written to two managed object paths in the private `ycloud` bucket. Downloads try both paths and accept a chunk only when its SHA-256 checksum matches metadata.

## UI capabilities

- My Files: upload, search, sort, grid/list, download, version history and delete
- Versions: inspect and download historical versions
- System Health: metadata query and representative replica-read checks
- Account: account information and password update
- Settings: local layout and refresh preferences
