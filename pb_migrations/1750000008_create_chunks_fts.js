/// <reference path="../pb_data/types.d.ts" />

// FTS5 virtual table mirroring `chunks` for lexical retrieval.
// External-content pattern (content='chunks', content_rowid='rowid') keeps the FTS index
// synchronized via AFTER INSERT/UPDATE/DELETE triggers on the chunks base table.
//
// Indexed columns: text, characters_present (stringified JSON works fine for FTS),
// location. unindexed columns are not added — we only search these three.
//
// Spoiler firewall:
//   FTS5 cannot filter on non-indexed columns directly, so retrieval queries must JOIN
//   chunks on rowid and apply WHERE chunks.spoiler_max_episode <= :before_episode
//   (and WHERE chunks.show_id = :show_id) server-side. See backend/retrieve.py.
migrate((db) => {
  // 1) Create the FTS5 virtual table.
  //    `content='chunks'` → external content; the FTS table doesn't store the text itself,
  //    only the inverted index pointing at chunks.rowid. `content_rowid='rowid'` is the
  //    SQLite implicit rowid on the chunks base table.
  db.newQuery(`
    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
      text,
      characters_present,
      location,
      content='chunks',
      content_rowid='rowid',
      tokenize='porter unicode61 remove_diacritics 2'
    )
  `).execute();

  // 2) Backfill: index any rows already present in chunks at migration time.
  db.newQuery(`
    INSERT INTO chunks_fts (rowid, text, characters_present, location)
    SELECT rowid, text, characters_present, location FROM chunks
  `).execute();

  // 3) Triggers to keep chunks_fts in lockstep with chunks.
  //    Standard SQLite FTS5 external-content sync pattern:
  //    - AFTER INSERT  → INSERT into FTS
  //    - AFTER DELETE  → INSERT 'delete' command row into FTS (FTS5 idiom)
  //    - AFTER UPDATE  → delete-then-insert
  db.newQuery(`
    CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
      INSERT INTO chunks_fts(rowid, text, characters_present, location)
      VALUES (new.rowid, new.text, new.characters_present, new.location);
    END
  `).execute();

  db.newQuery(`
    CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
      INSERT INTO chunks_fts(chunks_fts, rowid, text, characters_present, location)
      VALUES ('delete', old.rowid, old.text, old.characters_present, old.location);
    END
  `).execute();

  db.newQuery(`
    CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
      INSERT INTO chunks_fts(chunks_fts, rowid, text, characters_present, location)
      VALUES ('delete', old.rowid, old.text, old.characters_present, old.location);
      INSERT INTO chunks_fts(rowid, text, characters_present, location)
      VALUES (new.rowid, new.text, new.characters_present, new.location);
    END
  `).execute();
}, (db) => {
  // Down-migration: drop triggers first, then the virtual table.
  db.newQuery(`DROP TRIGGER IF EXISTS chunks_au`).execute();
  db.newQuery(`DROP TRIGGER IF EXISTS chunks_ad`).execute();
  db.newQuery(`DROP TRIGGER IF EXISTS chunks_ai`).execute();
  db.newQuery(`DROP TABLE IF EXISTS chunks_fts`).execute();
});
