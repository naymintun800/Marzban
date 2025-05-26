ARG PYTHON_VERSION=3.12

FROM python:$PYTHON_VERSION-slim AS build

ENV PYTHONUNBUFFERED=1

WORKDIR /code

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl unzip gcc python3-dev libpq-dev \
    && curl -L https://github.com/Gozargah/Marzban-scripts/raw/master/install_latest_xray.sh | bash \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/
RUN python3 -m pip install --upgrade pip setuptools \
    && pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Dashboard build stage
FROM node:18-slim AS dashboard-build

WORKDIR /dashboard
COPY ./app/dashboard /dashboard
RUN npm ci \
    && VITE_BASE_API=/api/ npm run build -- --outDir build --assetsDir statics \
    && cp ./build/index.html ./build/404.html

FROM python:$PYTHON_VERSION-slim

ENV PYTHON_LIB_PATH=/usr/local/lib/python${PYTHON_VERSION%.*}/site-packages
WORKDIR /code

RUN rm -rf $PYTHON_LIB_PATH/*

COPY --from=build $PYTHON_LIB_PATH $PYTHON_LIB_PATH
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /usr/local/share/xray /usr/local/share/xray

COPY . /code

# Copy the built dashboard from the dashboard-build stage
COPY --from=dashboard-build /dashboard/build /code/app/static

RUN ln -s /code/marzban-cli.py /usr/bin/marzban-cli \
    && chmod +x /usr/bin/marzban-cli \
    && marzban-cli completion install --shell bash

# Create a start script to ensure migrations run correctly
RUN echo '#!/bin/bash\n\
echo "Running database migrations..."\n\
alembic upgrade head\n\
echo "Starting Marzban..."\n\
python main.py' > /code/start.sh && chmod +x /code/start.sh

CMD ["/code/start.sh"]
