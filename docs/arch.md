# NatureDB 

## Blueprints
base: portals, basic views
frontpage: 有語系


## sites

- app/static/sites
- app/templates/sites

## Javascript

- rewrite in svelte (original in vanilla javascript)
- folder: client
- apps:
  - data-search: as component
  - record-form: record-form page edit with index.html

docker copy build frontend dist to `/build`, use `send_from_directory` to get file
