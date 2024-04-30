ARG PYTHON_VERSION
ARG DEBIAN_RELEASE
ARG NODE_VERSION

# Stage 1: Build the svelte code
FROM node:${NODE_VERSION}-alpine as client-search

WORKDIR /app
COPY client/data-search/package.json \
     client/data-search/package-lock.json \
     .

RUN npm install
COPY client/data-search/src ./src
COPY client/data-search/jsconfig.json \
     client/data-search/.env.production \
     client/data-search/svelte.config.js \
     client/data-search/vite.config.js \
     client/data-search/index.html \
     .
RUN npm run build

# Stage 2: Build the svelte code for admin
FROM node:${NODE_VERSION}-alpine as client-admin

WORKDIR /app
COPY client/admin-record/package.json \
     client/admin-record/package-lock.json \
     .

RUN npm install
COPY client/admin-record/src ./src
COPY client/admin-record/jsconfig.json \
     client/admin-record/.env.production \
     client/admin-record/svelte.config.js \
     client/admin-record/vite.config.js \
     client/admin-record/index.html \
     .
RUN npm run build

# Stage 3: Create the flask app
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_RELEASE} AS builder

ARG PIP_REQUIREMENTS

RUN apt-get update \
  && apt-get install -y build-essential \
  && apt-get purge -y --auto-remove \
  && rm -fr /var/lib/apt/lists/*

WORKDIR /code

#flask static

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements requirements
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r ${PIP_REQUIREMENTS}

COPY --from=client-search /app/dist /app/static/data-search-svelte
COPY --from=client-admin /app/dist /app/blueprints/admin_static/record-form

COPY ./docker/entrypoint /srv/entrypoint
RUN sed -i 's/\r$//g' /srv/entrypoint
RUN chmod +x /srv/entrypoint

COPY ./docker/start /srv/start
RUN sed -i 's/\r$//g' /srv/start
RUN chmod +x /srv/start

ENV FLASK_APP=wsgi.py
ENV FLASK_DEBUG=1
ENV FLASK_ENV=development

ENTRYPOINT ["/srv/entrypoint"]