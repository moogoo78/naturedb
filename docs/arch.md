# NatureDB 

## Blueprints
base: portals, basic views
frontpage: 有語系


## sites

- app/static/sites
- app/templates/sites

site.data struct

```json
{
    "admin": {
        "form": {
            "collection_id": [["Category", [["field1", "field2"]]]],
        },
        "uploads": {
            "bucket": "some-bucket",
            "prefix": "path/to",
            "region": "ap-northeast-1",
            "storage": "aws"
        },
        "record_list_fields": {
            "accession_number": "voucher_id",
            "collector": "collector",
            "collector_zh": "collector_zh",
            "full_scientific_name": "species_name",
            "common_name": "species_name_zh",
            "country": "country",
            "county": "county",
            "localityc": "localityc",
            "locality": "locality,"
        }
    },
    "pages": {
        "reference": "reference",
        "sample-preparation": "/sample-preparation"
    },
    "phase": 1,
    "fields": {
        "field1": ["label of field1"], "field2": ["label of field2"]
    }
}
```

## Javascript

- rewrite in svelte (original in vanilla javascript)
- folder: client
- apps:
  - data-search: as component
  - record-form: record-form page edit with index.html

docker copy build frontend dist to `/build`, use `send_from_directory` to get file

## Image Size

s:
m:
l:
x:
o:

## settings
```
json: {
  key: value
}
```
如果json格式錯, 會影響架構


gridjs
tom-select

tailwindcss + flowbite



customable layout
- total custom: add folder in templates/sites
- part custom: add folder in tempaltes/sites, part: navbar, footer_links
- static pages: settings/{site}.json, pages: [url]: [template.html]

can use:
- site.get_type_specimens
- related_links



ark/noid
ref:

[docker-arknoid/d/arknoid at main · jkunze/docker-arknoid](https://github.com/jkunze/docker-arknoid/blob/main/d/arknoid)
[noid/noid/pynoid.py at master · emdb-empiar/noid](https://github.com/emdb-empiar/noid/blob/master/noid/pynoid.py#L121)
[noid - nice opaque identifier generator commands - metacpan.org](https://metacpan.org/dist/Noid/view/noid)
