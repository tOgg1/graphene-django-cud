.PHONY: test
test:
	pipenv run py.test

.PHONY: test-cov
test-cov:
	pipenv run py.test --cov=.

.PHONY: test-watch
test-watch:
	pipenv run ptw -- --testmon

.PHONY: migrate
migrate:
	pipenv run python manage.py migrate

.PHONY: migrations
migrations:
	pipenv run python manage.py makemigrations

.PHONY: run
run:
	pipenv run python manage.py runserver

.PHONY: shell
shell:
	pipenv run python manage.py shell

.PHONY: superuser
superuser:
	pipenv run python manage.py createsuperuser

.PHONY: worker
worker:
	pipenv run celery -A firmadok worker -l INFO

.PHONY: beat
beat:
	pipenv run celery -A firmadok beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler

.PHONY: build
build:
	python setup.py sdist bdist_wheel


.PHONY: release
release:
	twine upload dist/*


