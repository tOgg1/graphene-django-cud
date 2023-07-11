.PHONY: test
test:
	poetry run py.test

.PHONY: test-cov
test-cov:
	poetry run py.test --cov=.

.PHONY: test-watch
test-watch:
	poetry run ptw -- --testmon

.PHONY: migrate
migrate:
	poetry run python manage.py migrate

.PHONY: migrations
migrations:
	poetry run python manage.py makemigrations

.PHONY: run
run:
	poetry run python manage.py runserver

.PHONY: shell
shell:
	poetry run python manage.py shell

.PHONY: superuser
superuser:
	poetry run python manage.py createsuperuser

.PHONY: build
build:
	python setup.py sdist bdist_wheel


.PHONY: release
release:
	poetry run twine upload dist/*
