# Development

1. git clone this repo
2. set `.env`
    - ACME_EMAIL must set right, or let's encrypt certificate will error
    - WEB_ENV set dev
3. edit compose.prod-vhost.yml from example file
4.  put database dump gzipped file initdb folder
5. docker compose up
6. update site host value by
    - exec postgres
    - `UPDATE site set host={my-domain} WHILE id = {my-id}`
7. copy settings to app/settings/mysite.json

### Github Action

`ssh-gen`

create `id_rsa-github` and `id_rsa.github.pub`

in server:

```sh
cat id_rsa.github.pub >> ~/.ssh/authorized
```

In Github repo setting page:

copy id_rsa-github (private) to github settings page, set secrets `$KEY`
