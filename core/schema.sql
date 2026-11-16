-- Game database schema. Times are Unix seconds. JSON columns hold flexible game data.

CREATE TABLE IF NOT EXISTS players (
    user_id      INTEGER PRIMARY KEY,
    gold         INTEGER NOT NULL DEFAULT 0 CHECK (gold >= 0),
    shards       INTEGER NOT NULL DEFAULT 0 CHECK (shards >= 0),
    gems         INTEGER NOT NULL DEFAULT 0 CHECK (gems >= 0),
    pity         INTEGER NOT NULL DEFAULT 0,          -- failed rerolls since the last T4 or T5
    level        INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
    xp           INTEGER NOT NULL DEFAULT 0 CHECK (xp >= 0),   -- XP towards the next level
    created_at   INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS items (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,      -- internal key, used by loadouts
    uid          TEXT NOT NULL UNIQUE,                  -- public code players type, like H12 (slot letter + count)
    owner_id     INTEGER NOT NULL REFERENCES players(user_id),
    slot         TEXT NOT NULL,                        -- weapon, helmet, chestplate, leggings, boots
    rarity       TEXT NOT NULL,
    element      TEXT NOT NULL DEFAULT 'neutral',
    base_json    TEXT NOT NULL,                        -- base stats
    affix_json   TEXT NOT NULL,                        -- [{stat, tier, value, locked}]
    created_at   INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_items_owner ON items(owner_id);

CREATE TABLE IF NOT EXISTS loadouts (
    user_id      INTEGER NOT NULL REFERENCES players(user_id),
    preset       INTEGER NOT NULL CHECK (preset BETWEEN 1 AND 3),
    weapon_id      INTEGER REFERENCES items(id),
    helmet_id      INTEGER REFERENCES items(id),
    chestplate_id  INTEGER REFERENCES items(id),
    leggings_id    INTEGER REFERENCES items(id),
    boots_id       INTEGER REFERENCES items(id),
    disposition  TEXT NOT NULL DEFAULT 'balanced',     -- async policy: aggressive, balanced, defensive
    PRIMARY KEY (user_id, preset)
);

CREATE TABLE IF NOT EXISTS expeditions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES players(user_id),
    zone         TEXT NOT NULL,
    started_at   INTEGER NOT NULL,
    ends_at      INTEGER NOT NULL,
    state        TEXT NOT NULL DEFAULT 'running'
                 CHECK (state IN ('running', 'claimed', 'lost')),
    seed         INTEGER NOT NULL,
    haul_json    TEXT NOT NULL DEFAULT '{}'
);
-- "ready" is not stored: a running expedition is ready once ends_at has passed.
CREATE INDEX IF NOT EXISTS idx_expeditions_user ON expeditions(user_id, state);

CREATE TABLE IF NOT EXISTS duels (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    mode         TEXT NOT NULL CHECK (mode IN ('live', 'async')),
    player_a     INTEGER NOT NULL REFERENCES players(user_id),
    player_b     INTEGER NOT NULL REFERENCES players(user_id),
    winner_id    INTEGER REFERENCES players(user_id),  -- NULL means a draw
    rounds       INTEGER NOT NULL,
    seed         INTEGER NOT NULL,
    log_json     TEXT NOT NULL,
    created_at   INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_duels_players ON duels(player_a, player_b);

-- Named counters. Item codes use one counter per slot (item_weapon, item_helmet ...), so a
-- code is never reused, even after items are deleted.
CREATE TABLE IF NOT EXISTS counters (
    name   TEXT PRIMARY KEY,
    value  INTEGER NOT NULL DEFAULT 0
);
