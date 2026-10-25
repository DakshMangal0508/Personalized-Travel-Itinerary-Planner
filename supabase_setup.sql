-- Run this in Supabase SQL Editor after creating the public.trips table.
-- Expected existing columns: id, destination, itinerary (jsonb), created_at.

alter table public.trips
  add column if not exists owner_id uuid references auth.users(id) on delete cascade;

create index if not exists trips_owner_created_at_idx
  on public.trips (owner_id, created_at desc);

alter table public.trips enable row level security;

drop policy if exists "Users can read their own trips" on public.trips;
create policy "Users can read their own trips"
  on public.trips for select to authenticated
  using ((select auth.uid()) = owner_id);

drop policy if exists "Users can create their own trips" on public.trips;
create policy "Users can create their own trips"
  on public.trips for insert to authenticated
  with check ((select auth.uid()) = owner_id);

drop policy if exists "Users can update their own trips" on public.trips;
create policy "Users can update their own trips"
  on public.trips for update to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);

grant usage on schema public to authenticated;
grant select, insert, update on public.trips to authenticated;
