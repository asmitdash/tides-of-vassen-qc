/// <reference path="../pb_data/types.d.ts" />

// Collection: shows
// id (text, primary - inherited from PB), title (text, required), franchise_id (text, optional)
migrate((db) => {
  const collection = new Collection({
    id: "pbc_shows0001",
    name: "shows",
    type: "base",
    system: false,
    schema: [
      {
        id: "shows_title",
        name: "title",
        type: "text",
        required: true,
        presentable: true,
        unique: false,
        options: {
          min: 1,
          max: 500,
          pattern: ""
        }
      },
      {
        id: "shows_franchise",
        name: "franchise_id",
        type: "text",
        required: false,
        presentable: false,
        unique: false,
        options: {
          min: null,
          max: 200,
          pattern: ""
        }
      }
    ],
        listRule: "",
    viewRule: "",
    createRule: null,
    updateRule: null,
    deleteRule: null,
    options: {}
  });

  return Dao(db).saveCollection(collection);
}, (db) => {
  const dao = new Dao(db);
  const collection = dao.findCollectionByNameOrId("shows");
  return dao.deleteCollection(collection);
});
