FROM python:3.12-alpine

RUN apk update && apk upgrade && apk add postgresql-dev gcc python3-dev musl-dev libffi-dev

WORKDIR /app

COPY ./ /app

RUN pip install -U poetry
RUN poetry config virtualenvs.create false
RUN poetry install --only main --no-interaction --no-root

ENV FLASK_APP=app:create_app
EXPOSE 5000
CMD ["flask", "run", "--host", "0.0.0.0"]
