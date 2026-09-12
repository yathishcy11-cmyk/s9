# Free Supabase deployment

This is the genuinely free online deployment path. It uses Supabase Free for Authentication, Postgres and Storage, and keeps GitHub Pages as the frontend host.

Current Supabase Free limits include 500 MB database size, 1 GB file storage, 5 GB egress and a 50 MB maximum file upload size. Free projects can pause after one week of inactivity. See the official pricing page before deploying.

## Setup

1. Create a Supabase account and a new Free project.
2. Open SQL Editor.
3. Paste and run `schema.sql`.
4. Open Project Settings → API.
5. Copy the Project URL and the `anon` public key.
6. Put them into `frontend/config.js`.
7. Commit/push the repository to GitHub.
8. Open your GitHub Pages URL.

## Important storage design

Each 5 MB chunk is stored twice in the private `ycloud` bucket:

```text
<user-id>/<version-id>/<chunk-index>/replica-a
<user-id>/<version-id>/<chunk-index>/replica-b
```

The browser downloads a verified replica for each chunk and reconstructs the original file. This is real persistent storage, but the two replicas are managed copies inside Supabase Storage rather than two independently hosted physical storage servers.

Because the Free plan includes 1 GB of storage, the two-copy design means the practical original-file capacity is roughly 500 MB before overhead. Keep the project within the published free quotas to avoid charges.
