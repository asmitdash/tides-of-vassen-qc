/// <reference path="../pb_data/types.d.ts" />

// Collection: canonical_facts
// id, show_id (relation), fact_type (character_knowledge|character_state|world_rule|relationship|object_state|location),
// subject_id (text), predicate (text), object_value (json),
// valid_from (json), valid_until (json), source_chunk_ids (json), confidence (number), canonicity (text, default 'aired')
migrate((db) => {
  const dao = new Dao(db);
  const showsCollection = dao.findCollectionByNameOrId("shows");

  const collection = new Collection({
    id: "pbc_facts000001",
    name: "canonical_facts",
    type: "base",
    system: false,
    schema: [
      {
        id: "cf_show_id",
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
        id: "cf_fact_type",
        name: "fact_type",
        type: "text",
        required: true,
        presentable: false,
        unique: false,
        options: {
          min: null,
          max: 50,
          pattern: "^(character_knowledge|character_state|world_rule|relationship|object_state|location)$"
        }
      },
      {
        id: "cf_subject",
        name: "subject_id",
        type: "text",
        required: true,
        presentable: true,
        unique: false,
        options: { min: 1, max: 200, pattern: "" }
      },
      {
        id: "cf_predicate",
        name: "predicate",
        type: "text",
        required: true,
        presentable: false,
        unique: false,
        options: { min: 1, max: 500, pattern: "" }
      },
      {
        id: "cf_object_value",
        name: "object_value",
        type: "json",
        required: false,
        presentable: false,
        unique: false,
        options: { maxSize: 2000000 }
      },
      {
        id: "cf_valid_from",
        name: "valid_from",
        type: "json",
        required: false,
        presentable: false,
        unique: false,
        options: { maxSize: 2000000 }
      },
      {
        id: "cf_valid_until",
        name: "valid_until",
        type: "json",
        required: false,
        presentable: false,
        unique: false,
        options: { maxSize: 2000000 }
      },
      {
        id: "cf_source_chunks",
        name: "source_chunk_ids",
        type: "json",
        required: false,
        presentable: false,
        unique: false,
        options: { maxSize: 2000000 }
      },
      {
        id: "cf_confidence",
        name: "confidence",
        type: "number",
        required: false,
        presentable: false,
        unique: false,
        options: { min: 0, max: 1, noDecimal: false }
      },
      {
        id: "cf_canonicity",
        name: "canonicity",
        type: "text",
        required: false,
        presentable: false,
        unique: false,
        options: { min: null, max: 50, pattern: "" }
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
  const collection = dao.findCollectionByNameOrId("canonical_facts");
  return dao.deleteCollection(collection);
});
