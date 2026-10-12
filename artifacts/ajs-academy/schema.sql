-- Apply deliberately to the target database before publishing; never run DDL at startup.
CREATE TABLE IF NOT EXISTS academy_state (
    id integer PRIMARY KEY,
    data jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS academy_auth_attempts (
    key text PRIMARY KEY,
    failures integer NOT NULL DEFAULT 0,
    blocked_until timestamptz
);
