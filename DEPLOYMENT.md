# Supabase + Render setup

1. In Supabase, run `supabase_setup.sql` in the SQL Editor. It adds per-user ownership and Row Level Security to the existing `public.trips` table. The table must have `destination` (text), `itinerary` (json/jsonb), and `created_at` columns; `id` should be its primary key.
2. Copy the Supabase project URL and publishable API key. Do not use or commit a secret/service-role key.
3. For local development, copy `.env.example` to `.env` and set both values. The app loads this file automatically; `.env` is excluded from Git.
4. Push the project to GitHub. In Render, create a Blueprint from the repository. Render reads `render.yaml` and prompts for `SUPABASE_URL` and `SUPABASE_KEY`.
5. After Render creates the service, copy its public URL into Supabase **Authentication → URL Configuration** as the Site URL and add it to the Redirect URLs. Email confirmation can be enabled; users must confirm before their first sign-in.

The app uses Supabase email/password authentication. Each user can read, create, and update only their own trips under the RLS policies in `supabase_setup.sql`.
