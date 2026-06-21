/// <reference path="../pb_data/types.d.ts" />

// Collection: episodes
// id, show_id (relation→shows), season (number), episode (number), title (text), canonicity (text, default 'aired')
migrate((db) => {
  const dao = new Dao(db);
  const showsCollection = dao.findCollectionByNameOrId("shows");

  const collection = new Collection({
    id: "pbc_episodes001",
    name: "episodes",
    type: "base",
    system: false,
    schema: [
      {
        id: "ep_show_id",
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
        id: "ep_season",
        name: "season",
        type: "number",
        required: true,
        presentable: false,
        unique: false,
        options: {
          min: 0,
          max: null,
          noDecimal: true
        }
      },
      {
        id: "ep_episode",
        name: "episode",
        type: "number",
        required: true,
        presentable: false,
        unique: false,
        options: {
          min: 0,
          max: null,
          noDecimal: true
        }
      },
      {
        id: "ep_title",
        name: "title",
        type: "text",
        required: false,
        presentable: true,
        unique: false,
        options: {
          min: null,
          max: 500,
          pattern: ""
        }
      },
      {
        id: "ep_canonicity",
        name: "canonicity",
        type: "text",
        required: false,
        presentable: false,
        unique: false,
        options: {
          min: null,
          max: 50,
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

  return dao.saveCollection(collection);
}, (db) => {
  const dao = new Dao(db);
  const collection = dao.findCollectionByNameOrId("episodes");
  return dao.deleteCollection(collection);
});
