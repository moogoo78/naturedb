# NatureDB, Yet Another Natural History Collection Management System

The "NaturalDB" is an open-source platform designed to manage, collect, and showcase natural history specimens and biodiversity data. This platform supports institutions in cataloging, curating, and publish the collections to other biodiversity information standards, like [Darwin core](https://dwc.tdwg.org/).

The following are some online examples:

| Cdoe | Title | Chinese Title | URL | status |
| ---- | ----- | --------------| --- | ------ |
| HAST | Biodiversity Research Museum, Herbarium, Academia Sinica | 中央研究院植物標本館 | https://hast.biodiv.tw | release 🟢 |
| TaiBOL | Taiwan Barcode of Life | 台灣野生生物遺傳物質冷凍典藏計畫 | https://taibol.biodiv.tw | beta🟡 |
| PPI | National Pingtung University of Science and Technology | 國立屏東科技大學森林系植物標本館 | https://ppi.naturedb.org/data | alpha 🔴 |
| ASIZ | Biodiversity Research Museum, Academia Sinica | 中央研究院動物標本館 | https://asiz.naturedb.org | alpha 🔴 |

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Data Management](#data-management)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Features

- **Specimen Data Integration**: Collect, manage, and display natural history specimen data from museums and research institutions worldwide.
- **Diversity Data Visualization**: Offers rich data visualization tools to explore biodiversity patterns.
- **API Support**: Provides an open API for third-party application integration.
- **Collection Management**: Tools for cataloging and curating specimens, including metadata management, tagging, and categorization.
- **Multilingual Support**: The platform supports traditional Chinese and English.
- **Dashboard**: can edit specimen collection data, and generate reports on collection statistics, specimen inventory, and data usage.

## Installation

### Prerequisites

- **Docker** with the Compose plugin. Nothing else is needed on the host —
  Python, PostgreSQL/PostGIS, Redis and Node all run inside the containers.

### Quick start (example site)

This gets you a running site with example data — one organization, one
collection, a small taxon backbone, a gazetteer, 8 specimen records and an
admin account — so you can click through the whole system before importing
anything of your own.

```bash
git clone https://github.com/TaiBIF/naturedb.git
cd naturedb
cp dotenv.sample .env

docker compose up -d --build        # builds, starts, and runs the migrations
docker compose exec flask flask initdata
```

Then open:

| What | URL | Notes |
| ---- | --- | ----- |
| Frontend | http://localhost:5000/ | browse, search, specimen detail |
| Admin | http://localhost:5000/admin/login | log in as `admin` / `admin` |
| Adminer | http://localhost:8080/ | server `postgres`, credentials from `.env` |

`flask initdata` is idempotent, so re-running it only fills in rows that are
missing. It refuses to run if site id 1 already belongs to a site other than
`demo`, so it will not touch a database restored from a production dump.

Non-default credentials:

```bash
docker compose exec flask flask initdata --admin-username curator --admin-password 's3cret'
```

(If your checkout has the optional `Makefile`, `make init` runs the same two
steps and prints the URLs.)

### What the example data contains

Defined in [`app/initdata.py`](app/initdata.py) — edit that file to reshape the
example, or use it as a template for seeding a real institution.

- **Site** `demo` bound to host `localhost:5000` (in dev, `Site.find_by_host()`
  also matches the first label of the Host header, so `demo.localhost:5000`
  works too), with its per-site settings in `app/settings/demo.json`.
- **Organization / collection**: `DEMO` — "Demo Herbarium".
- **Gazetteer**: `COUNTRY` / `ADM1` / `ADM2` classes plus the custom
  `national_park` and `locality` classes. These carry **fixed ids (5–10)** that
  the record form, the exporters and the quick-edit country dropdown depend on —
  keep them if you replace the data.
- **Taxa**: a three-family backbone (Fagaceae, Lauraceae, Asteraceae) with the
  `taxon_relation` closure rows filled in.
- **Specimens**: 8 records / 9 units with collectors, identifications,
  coordinates, altitudes, named areas and assertions (植群型, 生長型, …).
- **News**: two article categories and three articles.
- **User**: a `ROLE_ROOT` site administrator.

There are no specimen images: media lives in object storage (see
`admin.uploads` in the site settings), so a self-contained example ships
without it.

### Setting up your own site

1. Copy `app/settings/demo.json` to `app/settings/<your-site-name>.json` and
   edit it. `Site.get_settings()` reads that file by `Site.name`, so the
   filename must match.
2. Either edit `app/initdata.py` and re-run `flask initdata`, or create the
   site/organization/collection rows through Adminer and
   `flask createuser <username> <password> <site_id> <role>`.
3. Point a real hostname at the site by setting `site.host` in the database
   (dev also matches on `Site.name`, so `/etc/hosts` entries are optional
   locally).
4. Import your own specimens with
   `flask importdata <csv_file> <collection_id> <record_group>`.

### Production / staging

```bash
docker compose -f compose.yml -f compose.prod.yml up -d --build
```

`compose.prod.yml` adds Traefik with Let's Encrypt (set `ACME_EMAIL` and
`CF_DNS_API_TOKEN` in `.env`), gunicorn instead of the dev server, and the
PostgreSQL tuning knobs. Per-host router labels go in `compose.prod-vhosts.yml`
— see `compose.prod-vhosts-sample.yml`.

To start from a database dump instead of the example data, drop the gzipped
dump into `initdb/` before the first `up`; the postgres entrypoint loads
everything in that directory in filename order, after
`initdb/00-extensions.sql` has created PostGIS.

## Usage

1. **Browse Specimens**: Visit the homepage of the platform to search and browse natural history specimens.
2. **Pages**: Visit static pages like: about us, contact and dynamic pages: news, related links...
3. **API Usage**: not ready.

## Data Management (admin)

1. **Cataloging Specimens**: Use the collection management interface to catalog new specimens, including the input of metadata such as species name, collection date, location, and more.
2. **Curating Collections**: Organize specimens into collections, adding tags and categories to facilitate easy retrieval and browsing.
3. **User Roles and Permissions**: Assign roles such as administrator, curator, or researcher to manage who can add, edit, or view specific parts of the collection.
4. **Reporting**: Generate reports on the number of specimens, their condition, and other collection-related metrics to help manage the inventory and share insights with stakeholders.

## Contributing

We welcome contributions from developers, curators, and researchers! Here’s how you can get involved:

1. Fork the repository and clone it locally.
2. Create a new branch for your changes:
    ```bash
    git checkout -b my-feature-branch
    ```
3. Commit your changes and push them to your remote repository:
    ```bash
    git push origin my-feature-branch
    ```
4. Create a Pull Request, describing your changes.

## License

This project is licensed under the [MIT License](LICENSE). You are free to use, modify, and distribute this project, but please retain the original author's credit.

## Contact

If you have any questions or suggestions, feel free to reach out to us:

- **Email**: moogoo78@gmail.com
- **Issue Tracker**: [GitHub Issues](https://github.com/TaiBIF/naturaldb/issues)






