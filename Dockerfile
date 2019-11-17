
FROM tiangolo/uwsgi-nginx:python3.7-alpine3.7

# Copy app files.
COPY src/static /app/static
COPY src/templates /app/templates
COPY src/*.py /app/
COPY src/uwsgi.ini /app/

# Setup Python dependencies.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Setup Javascript dependencies.
RUN apk add nodejs
RUN npm install -g grunt-cli
COPY package.json .
COPY package-lock.json .
COPY Gruntfile.js .
RUN npm install
RUN grunt --env=docker

