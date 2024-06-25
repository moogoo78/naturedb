build:
	sudo docker compose build
up:
	sudo docker compose up
down:
	sudo docker compose down

deploy-sites:
	scp -r app/static/sites ndb:~/naturedb/app/static
	scp -r app/templates/sites ndb:~/naturedb/app/templates
