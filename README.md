# NatureDB, Yet Another Natural History Collection Management System

The "NaturalDB" is an open-source platform designed to manage, collect, and showcase natural history specimens and biodiversity data. This platform supports institutions in cataloging, curating, and publish the collections to other biodiversity information standards, like [Darwin core](https://dwc.tdwg.org/).

The following are some online examples:

| Cdoe | Title | Chinese Title | URL | status |
| ---- | ----- | --------------| --- | ------ |
| HAST | Biodiversity Research Museum, Herbarium, Academia Sinica | 中央研究院植物標本館 | https://hast.biodiv.tw | release 🟢 |
| TaiBOL | Taiwan Barcode of Life | 台灣野生生物遺傳物質冷凍典藏計畫 | https://taibol.biodiv.tw | beta🟡 |
| PPI | National Pingtung University of Science and Technology | 國立屏東科技大學森林系植物標本館 | https://ppi.naturedb.org/data | alpha 🔴 |

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

Before installing, ensure your system meets the following requirements:

- **Docker** (optional): For containerized deployment

### Installation Steps

1. Clone the repository:
    ```bash
    git clone https://github.com/TaiBIF/naturedb.git
    cd naturedb
    ```

2. Create .env:
    copy dotenv.sample & edit
    ```bash
    cp dotenv.sample .env
    ```

3. Build docker image:
   ```bash
   docker compose -f compose.yml -f compose.override.yml -f compose.upgrade.yml build
   ```

4. Initialize database

    ```text
    postgres: create database naturedb;
    flask migrate
    insert init-db.sql
    ```

5. Start the application:
    ```bash
    docker compose -f compose.yml -f compose.prod.yml up
    ```

6. Set local DNS:

edit `/etc/hosts`

```text
127.0.0.1 foo.bar.com
```

database table: site add domain field

insert site admin account

7. Visit `http://foo.bar.com:5000` in your browser to access the platform.

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






