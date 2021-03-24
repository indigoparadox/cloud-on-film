
FROM tiangolo/uwsgi-nginx:python3.7-alpine3.7

# Copy app files.
COPY src/uwsgi.ini /app/

# Setup Python dependencies.
RUN pip install -r .

