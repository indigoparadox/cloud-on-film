
FROM python:3.11

WORKDIR /code

# Copy app files.
COPY ./cloud_on_film /code/cloud_on_film
COPY ./setup.cfg /code
COPY ./setup.py /code
COPY ./README.md /code
COPY ./MANIFEST.in /code
COPY ./pyproject.toml /code
COPY ./requirements.txt /code

# Setup Python dependencies.
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
RUN pip install --no-cache-dir --upgrade mysql mysqlclient
RUN pip install --no-cache-dir --upgrade gunicorn

CMD ["gunicorn", "--bind", "0.0.0.0:80", "cloud_on_film:app"]

