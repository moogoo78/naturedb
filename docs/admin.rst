************
Admin
************

admin_register.py: configure, url routing, model mapping

list_collection_filter: related (back_populates), field (collection_id)


blueprint-admin
================
modify_frontend_collection_record
create_frontend_collection_record


Form Control
================


field type
--------------

- text: input
- select
  - foreign (Model)
  - options (fixed options, value: ['id', 'label'])
  - value.current_user and value.current_user == 'organization.collections' # HACK
  - textarea
  - date
  - number
  - boolean (select: 是/否) (**name: __bool__**)
  - organization_collections

- checkbox (name: **__m2m__collections__**)


API related
==============

register_api:
  - records: ItemAPI & ListAPI

user_list_category: FormView & GridView
person, taxon, article: ItemAPI1, ListAPI1
