FROM python:3.7-alpine

RUN apk update && apk upgrade && apk add postgresql-dev gcc python3-dev musl-dev

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

COPY ./ /app

ENV FLASK_APP=/app/app.py
EXPOSE 5000
CMD ["flask", "run", "--host", "0.0.0.0"]
