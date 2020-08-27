FROM python:3.8-alpine

RUN apk update && apk upgrade && apk add postgresql-dev gcc python3-dev musl-dev libffi-dev

WORKDIR /app

COPY ./ /app

RUN pip install -U --pre pip poetry
RUN poetry config virtualenvs.create false
RUN poetry install

ENV FLASK_APP=/app/app.py
EXPOSE 5000
CMD ["flask", "run", "--host", "0.0.0.0"]
