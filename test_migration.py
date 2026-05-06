import sqlite3

def migrate(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # 1. Add deployment_id if missing
    for table in ["adm_snapshots", "activity_snapshots", "custom_timers", "system_annotations", "jump_bridges"]:
        cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        if "deployment_id" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN deployment_id TEXT NOT NULL DEFAULT 'lawn-kalevala'")

    # 2. Rebuild system_annotations to update UNIQUE constraint
    # We check if it has the new constraint by checking the SQL
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='system_annotations'").fetchone()
    if row and "UNIQUE(deployment_id, system_name)" not in row["sql"].replace(" ", ""):
        print("Migrating system_annotations...")
        conn.executescript("""
            CREATE TABLE system_annotations_new (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_id TEXT NOT NULL DEFAULT 'lawn-kalevala',
                system_name TEXT NOT NULL,
                note        TEXT NOT NULL,
                updated_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                UNIQUE(deployment_id, system_name)
            );
            INSERT INTO system_annotations_new (id, deployment_id, system_name, note, updated_at)
            SELECT id, deployment_id, system_name, note, updated_at FROM system_annotations;
            DROP TABLE system_annotations;
            ALTER TABLE system_annotations_new RENAME TO system_annotations;
            CREATE INDEX IF NOT EXISTS idx_annotation_system ON system_annotations(system_name);
        """)

    # 3. Rebuild jump_bridges to update UNIQUE constraint
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='jump_bridges'").fetchone()
    if row and "UNIQUE(deployment_id, system_a, system_b)" not in row["sql"].replace(" ", ""):
        print("Migrating jump_bridges...")
        conn.executescript("""
            CREATE TABLE jump_bridges_new (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                deployment_id TEXT NOT NULL DEFAULT 'lawn-kalevala',
                system_a   TEXT NOT NULL,
                system_b   TEXT NOT NULL,
                label      TEXT,
                created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                UNIQUE(deployment_id, system_a, system_b)
            );
            INSERT INTO jump_bridges_new (id, deployment_id, system_a, system_b, label, created_at)
            SELECT id, deployment_id, system_a, system_b, label, created_at FROM jump_bridges;
            DROP TABLE jump_bridges;
            ALTER TABLE jump_bridges_new RENAME TO jump_bridges;
        """)
        
    conn.commit()
    conn.close()

migrate("intel.db")
