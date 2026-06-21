/// <reference path="../pb_data/types.d.ts" />

// Collection: flags
// id, run_id (text), show_id (relation), draft_episode (number), draft_scene (text),
// draft_line_range (json), severity (text), flag_type (plot_hole|continuity), summary (text),
// evidence (json), reasoning_trace (json), verifier_outcome (text), self_consistency (json),
// surfaced (bool, default true), created (autodate)
migrate((db) => {
  const dao = new Dao(db);
  const showsCollection = dao.findCollectionByNameOrId("shows");

  const collection = new Collection({
    id: "pbc_flags000001",
    name: "flags",
    type: "base",
    system: false,
    schema: [
      {
        id: "fl_run_id",
        name: "run_id",
        type: "text",
        required: false,
        presentable: false,
        unique: false,
        options: { min: null, max: 100, pattern: "" }
      },
      {
        id: "fl_show_id",
        name: "show_id",
        type: "relation",
        required: true,
        presentable: false,
        unique: false,
        options: {
          collectionId: showsCollection.id,
          cascadeDelete: true,
          minSelect: null,
          maxSelect: 1,
          displayFields: null
        }
      },
      {
        id: "fl_draft_ep",
        name: "draft_episode",
        type: "number",
        required: false,
        presentable: false,
        unique: false,
        options: { min: 0, max: null, noDecimal: true }
      },
      {
        id: "fl_draft_scene",
        name: "draft_scene",
        type: "text",
        required: false,
        presentable: false,
        unique: false,
        options: { min: null, max: 200, pattern: "" }
      },
      {
        id: "fl_line_range",
        name: "draft_line_range",
        type: "json",
        required: false,
        presentable: false,
        unique: false,
        options: { maxSize: 100000 }
      },
      {
        id: "fl_severity",
        name: "severity",
        type: "text",
        required: false,
        presentable: false,
        unique: false,
        options: { min: null, max: 50, pattern: "" }
      },
      {
        id: "fl_flag_type",
        name: "flag_type",
        type: "text",
        required: true,
        presentable: false,
        unique: false,
        options: { min: null, max: 50, pattern: "^(plot_hole|continuity)$" }
      },
      {
        id: "fl_summary",
        name: "summary",
        type: "text",
        required: false,
        presentable: true,
        unique: false,
        options: { min: null, max: 5000, pattern: "" }
      },
      {
        id: "fl_evidence",
        name: "evidence",
        type: "json",
        required: false,
        presentable: false,
        unique: false,
        options: { maxSize: 5000000 }
      },
      {
        id: "fl_reasoning",
        name: "reasoning_trace",
        type: "json",
        required: false,
        presentable: false,
        unique: false,
        options: { maxSize: 5000000 }
      },
      {
        id: "fl_verifier",
        name: "verifier_outcome",
        type: "text",
        required: false,
        presentable: false,
        unique: false,
        options: { min: null, max: 100, pattern: "" }
      },
      {
        id: "fl_self_consistency",
        name: "self_consistency",
        type: "json",
        required: false,
        presentable: false,
        unique: false,
        options: { maxSize: 1000000 }
      },
      {
        id: "fl_surfaced",
        name: "surfaced",
        type: "bool",
        required: false,
        presentable: false,
        unique: false,
        options: {}
      },
      {
        id: "fl_created",
        name: "created",
        type: "autodate",
        required: false,
        presentable: false,
        unique: false,
        options: { onCreate: true, onUpdate: false }
      }
    ],
        listRule: "",
    viewRule: "",
    createRule: null,
    updateRule: null,
    deleteRule: null,
    options: {}
  });

  return dao.saveCollection(collection);
}, (db) => {
  const dao = new Dao(db);
  const collection = dao.findCollectionByNameOrId("flags");
  return dao.deleteCollection(collection);
});
