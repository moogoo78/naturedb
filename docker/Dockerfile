ARG PYTHON_VERSION
ARG DEBIAN_RELEASE

FROM python:${PYTHON_VERSION}-slim-${DEBIAN_RELEASE} AS builder

RUN apt-get update \
  && apt-get install -y build-essential \
  && apt-get purge -y --auto-remove \
  && rm -fr /var/lib/apt/lists/*

WORKDIR /code

#COPY --from=node
#flask static
COPY requirements requirements
RUN pip install --upgrade pip
RUN pip install --no-cache --user -r requirements/base.txt

#ENTRYPOINT ["python"]
#CMD ["app.py"]

COPY ./docker/entrypoint /srv/entrypoint
RUN sed -i 's/\r$//g' /srv/entrypoint
RUN chmod +x /srv/entrypoint

COPY ./docker/start /srv/start
RUN sed -i 's/\r$//g' /srv/start
RUN chmod +x /srv/start

ENV FLASK_APP=wsgi.py
ENV FLASK_DEBUG=1
ENV FLASK_ENV=development

# CMD ["/root/.local/bin/flask", "run", "--host", "0.0.0.0"]

ENTRYPOINT ["/srv/entrypoint"]