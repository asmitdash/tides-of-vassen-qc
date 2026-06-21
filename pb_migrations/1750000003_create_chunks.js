/// <reference path="../pb_data/types.d.ts" />

// Collection: chunks
// id, show_id (relation→shows), episode_id (relation→episodes), season, episode,
// scene (text), beat (number), chunk_type (text: script|bible|character|exemplar),
// text (required), characters_present (json), location (text), spoiler_max_episode (number), source_uri (text)
migrate((db) => {
  const dao = new Dao(db);
  const showsCollection = dao.findCollectionByNameOrId("shows");
  const episodesCollection = dao.findCollectionByNameOrId("episodes");

  const collection = new Collection({
    id: "pbc_chunks00001",
    name: "chunks",
    type: "base",
    system: false,
    schema: [
      {
        id: "ch_show_id",
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
        id: "ch_episode_id",
        name: "episode_id",
        type: "relation",
        required: false,
        presentable: false,
        unique: false,
        options: {
          collectionId: episodesCollection.id,
          cascadeDelete: false,
          minSelect: null,
          maxSelect: 1,
          displayFields: null
        }
      },
      {
        id: "ch_season",
        name: "season",
        type: "number",
        required: false,
        presentable: false,
        unique: false,
        options: { min: 0, max: null, noDecimal: true }
      },
      {
        id: "ch_episode",
        name: "episode",
        type: "number",
        required: false,
        presentable: false,
        unique: false,
        options: { min: 0, max: null, noDecimal: true }
      },
      {
        id: "ch_scene",
        name: "scene",
        type: "text",
        required: false,
        presentable: false,
        unique: false,
        options: { min: null, max: 200, pattern: "" }
      },
      {
        id: "ch_beat",
        name: "beat",
        type: "number",
        required: false,
        presentable: false,
        unique: false,
        options: { min: 0, max: null, noDecimal: true }
      },
      {
        id: "ch_chunk_type",
        name: "chunk_type",
        type: "text",
        required: true,
        presentable: false,
        unique: false,
        options: { min: null, max: 50, pattern: "^(script|bible|character|exemplar)$" }
      },
      {
        id: "ch_text",
        name: "text",
        type: "text",
        required: true,
        presentable: true,
        unique: false,
        options: { min: 1, max: null, pattern: "" }
      },
      {
        id: "ch_chars",
        name: "characters_present",
        type: "json",
        required: false,
        presentable: false,
        unique: false,
        options: { maxSize: 5000000 }
      },
      {
        id: "ch_location",
        name: "location",
        type: "text",
        required: false,
        presentable: false,
        unique: false,
        options: { min: null, max: 500, pattern: "" }
      },
      {
        id: "ch_spoiler_max",
        name: "spoiler_max_episode",
        type: "number",
        required: true,
        presentable: false,
        unique: false,
        options: { min: 0, max: null, noDecimal: true }
      },
      {
        id: "ch_source_uri",
        name: "source_uri",
        type: "text",
        required: false,
        presentable: false,
        unique: false,
        options: { min: null, max: 1000, pattern: "" }
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
  const collection = dao.findCollectionByNameOrId("chunks");
  return dao.deleteCollection(collection);
});
