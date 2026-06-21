/// <reference path="../pb_data/types.d.ts" />

// Repair migration: the original 1750000005_create_flags and 1750000006_create_runs
// migrations partially failed on first attempt (index-creation SQL error) and the
// retry without indexes ended up persisting EMPTY schemas in _collections — the
// fields never made it into the schema array. This migration deletes the empty
// flag/runs collections and re-creates them with the full schema we actually need.
//
// Idempotent: if the collections already have schemas, do nothing.

migrate((db) => {
  const dao = new Dao(db);

  // Helper: rebuild a collection only if its current schema is empty.
  function rebuildIfEmpty(name, builder) {
    let existing;
    try {
      existing = dao.findCollectionByNameOrId(name);
    } catch (e) {
      existing = null;
    }
    if (existing) {
      const schemaLen = existing.schema && existing.schema.length ? existing.schema.length : 0;
      if (schemaLen > 0) {
        return; // healthy — leave alone
      }
      dao.deleteCollection(existing);
    }
    const c = builder();
    dao.saveCollection(c);
  }

  const showsCollection = dao.findCollectionByNameOrId("shows");

  rebuildIfEmpty("flags", () => new Collection({
    id: "pbc_flags000001",
    name: "flags",
    type: "base",
    system: false,
    schema: [
      { id: "fl_run_id",     name: "run_id",        type: "text", options: { max: 100 } },
      { id: "fl_show_id",    name: "show_id",       type: "relation", required: true, options: { collectionId: showsCollection.id, cascadeDelete: true, maxSelect: 1 } },
      { id: "fl_draft_ep",   name: "draft_episode", type: "number", options: { min: 0, noDecimal: true } },
      { id: "fl_draft_scene",name: "draft_scene",   type: "text", options: { max: 200 } },
      { id: "fl_line_range", name: "draft_line_range", type: "json", options: { maxSize: 100000 } },
      { id: "fl_severity",   name: "severity",      type: "text", options: { max: 50 } },
      { id: "fl_flag_type",  name: "flag_type",     type: "text", required: true, options: { max: 50, pattern: "^(plot_hole|continuity)$" } },
      { id: "fl_summary",    name: "summary",       type: "text", presentable: true, options: { max: 5000 } },
      { id: "fl_evidence",   name: "evidence",      type: "json", options: { maxSize: 5000000 } },
      { id: "fl_reasoning",  name: "reasoning_trace", type: "json", options: { maxSize: 5000000 } },
      { id: "fl_verifier",   name: "verifier_outcome", type: "text", options: { max: 100 } },
      { id: "fl_self_consistency", name: "self_consistency", type: "json", options: { maxSize: 1000000 } },
      { id: "fl_surfaced",   name: "surfaced",      type: "bool" },
    ],
    listRule: "", viewRule: "", createRule: null, updateRule: null, deleteRule: null,
    options: {},
  }));

  rebuildIfEmpty("runs", () => new Collection({
    id: "pbc_runs0000001",
    name: "runs",
    type: "base",
    system: false,
    schema: [
      { id: "ru_show_id",    name: "show_id",     type: "relation", required: true, options: { collectionId: showsCollection.id, cascadeDelete: true, maxSelect: 1 } },
      { id: "ru_draft_ep",   name: "draft_episode", type: "number", options: { min: 0, noDecimal: true } },
      { id: "ru_surface",    name: "surface",     type: "text", options: { max: 50, pattern: "^(writers_room|qc)$" } },
      { id: "ru_input_text", name: "input_text",  type: "text" },
      { id: "ru_output",     name: "output",      type: "json", options: { maxSize: 5000000 } },
      { id: "ru_latency_ms", name: "latency_ms",  type: "number", options: { min: 0 } },
      { id: "ru_tokens_in",  name: "tokens_in",   type: "number", options: { min: 0 } },
      { id: "ru_tokens_out", name: "tokens_out",  type: "number", options: { min: 0 } },
      { id: "ru_cost_usd",   name: "cost_usd",    type: "number", options: { min: 0 } },
    ],
    listRule: "", viewRule: "", createRule: null, updateRule: null, deleteRule: null,
    options: {},
  }));
}, (db) => {
  // No-op down. We don't want to lose data if it was repopulated.
});
