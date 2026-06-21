/// <reference path="../pb_data/types.d.ts" />

// Collection: runs
// id, show_id (relation), draft_episode (number), surface (writers_room|qc), input_text (text),
// output (json), latency_ms (number), tokens_in (number), tokens_out (number), cost_usd (number), created (autodate)
migrate((db) => {
  const dao = new Dao(db);
  const showsCollection = dao.findCollectionByNameOrId("shows");

  const collection = new Collection({
    id: "pbc_runs0000001",
    name: "runs",
    type: "base",
    system: false,
    schema: [
      {
        id: "ru_show_id",
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
        id: "ru_draft_ep",
        name: "draft_episode",
        type: "number",
        required: false,
        presentable: false,
        unique: false,
        options: { min: 0, max: null, noDecimal: true }
      },
      {
        id: "ru_surface",
        name: "surface",
        type: "text",
        required: true,
        presentable: false,
        unique: false,
        options: { min: null, max: 50, pattern: "^(writers_room|qc)$" }
      },
      {
        id: "ru_input_text",
        name: "input_text",
        type: "text",
        required: false,
        presentable: false,
        unique: false,
        options: { min: null, max: null, pattern: "" }
      },
      {
        id: "ru_output",
        name: "output",
        type: "json",
        required: false,
        presentable: false,
        unique: false,
        options: { maxSize: 20000000 }
      },
      {
        id: "ru_latency",
        name: "latency_ms",
        type: "number",
        required: false,
        presentable: false,
        unique: false,
        options: { min: 0, max: null, noDecimal: false }
      },
      {
        id: "ru_tok_in",
        name: "tokens_in",
        type: "number",
        required: false,
        presentable: false,
        unique: false,
        options: { min: 0, max: null, noDecimal: true }
      },
      {
        id: "ru_tok_out",
        name: "tokens_out",
        type: "number",
        required: false,
        presentable: false,
        unique: false,
        options: { min: 0, max: null, noDecimal: true }
      },
      {
        id: "ru_cost",
        name: "cost_usd",
        type: "number",
        required: false,
        presentable: false,
        unique: false,
        options: { min: 0, max: null, noDecimal: false }
      },
      {
        id: "ru_created",
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
  const collection = dao.findCollectionByNameOrId("runs");
  return dao.deleteCollection(collection);
});
