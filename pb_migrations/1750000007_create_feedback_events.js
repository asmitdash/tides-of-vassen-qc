/// <reference path="../pb_data/types.d.ts" />

// Collection: feedback_events
// id, flag_id (relation→flags), user_action (accept|reject|explain), user_explanation (text), created (autodate)
migrate((db) => {
  const dao = new Dao(db);
  const flagsCollection = dao.findCollectionByNameOrId("flags");

  const collection = new Collection({
    id: "pbc_feedback0001",
    name: "feedback_events",
    type: "base",
    system: false,
    schema: [
      {
        id: "fb_flag_id",
        name: "flag_id",
        type: "relation",
        required: true,
        presentable: false,
        unique: false,
        options: {
          collectionId: flagsCollection.id,
          cascadeDelete: true,
          minSelect: null,
          maxSelect: 1,
          displayFields: null
        }
      },
      {
        id: "fb_action",
        name: "user_action",
        type: "text",
        required: true,
        presentable: false,
        unique: false,
        options: { min: null, max: 50, pattern: "^(accept|reject|explain)$" }
      },
      {
        id: "fb_explanation",
        name: "user_explanation",
        type: "text",
        required: false,
        presentable: false,
        unique: false,
        options: { min: null, max: null, pattern: "" }
      },
      {
        id: "fb_created",
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
  const collection = dao.findCollectionByNameOrId("feedback_events");
  return dao.deleteCollection(collection);
});
