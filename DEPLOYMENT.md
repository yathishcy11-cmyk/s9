# Deployment

## Supabase

1. Create a Supabase project.
2. Run `supabase/schema.sql` in the SQL Editor.
3. In Authentication → Sign In / Providers, enable Email.
4. For a classroom/internal deployment, email confirmation may be disabled if desired.
5. Copy the project URL and publishable key into `frontend/config.js`.

## GitHub Pages

The repository includes `.github/workflows/deploy-ycloud.yml`. Set GitHub Pages **Source** to **GitHub Actions**. Every push to `main` publishes the `frontend/` directory.

## Storage model

Each chunk is stored at two object paths:

```text
<user>/<version>/<chunk>/replica-a
<user>/<version>/<chunk>/replica-b
```

Metadata records the checksum and both paths. During download, YCloud verifies the checksum and falls back to the second replica if the first copy cannot be read or fails verification.
