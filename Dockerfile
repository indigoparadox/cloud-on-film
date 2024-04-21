
FROM python:3.11-alpine

WORKDIR /code

#RUN apt update && apt install -y nodejs npm
RUN apk update && apk add --no-cache --virtual .build-deps \
	gcc \
	libc-dev \
	linux-headers \
	mariadb-dev \
	python3-dev \
	postgresql-dev \
	nodejs \
	npm \
;

# Copy app files.
COPY ./cloud_on_film /code/cloud_on_film
COPY ./setup.cfg /code
COPY ./setup.py /code
COPY ./README.md /code
COPY ./MANIFEST.in /code
COPY ./pyproject.toml /code
COPY ./requirements.txt /code
COPY ./package.json /code
COPY ./package-lock.json /code
COPY ./Gruntfile.js /code

# Setup Python dependencies.
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
RUN pip install --no-cache-dir --upgrade mysql mysqlclient
RUN pip install --no-cache-dir --upgrade gunicorn

RUN npm install --global grunt
RUN npm install
RUN grunt

CMD ["gunicorn", "--bind", "0.0.0.0:80", "cloud_on_film:app"]

