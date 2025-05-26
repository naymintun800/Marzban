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

FROM python:$PYTHON_VERSION-slim

ENV PYTHON_LIB_PATH=/usr/local/lib/python${PYTHON_VERSION%.*}/site-packages
WORKDIR /code

RUN rm -rf $PYTHON_LIB_PATH/*

COPY --from=build $PYTHON_LIB_PATH $PYTHON_LIB_PATH
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /usr/local/share/xray /usr/local/share/xray

COPY . /code

RUN ln -s /code/marzban-cli.py /usr/bin/marzban-cli \
    && chmod +x /usr/bin/marzban-cli \
    && marzban-cli completion install --shell bash

# Create a debug script to check static files
RUN echo '#!/bin/bash\n\
echo "Checking static file paths..."\n\
ls -la /code/app/dashboard/build/ || echo "build dir not found"\n\
ls -la /code/app/dashboard/build/statics/ || echo "statics dir not found"\n\
echo "Creating backup of init.py..."\n\
cp /code/app/dashboard/__init__.py /code/app/dashboard/__init__.py.bak\n\
echo "Updating init.py..."\n\
sed -i "s|statics_dir = build_dir / '\''statics'\''|statics_dir = Path('\''/code/app/dashboard/build/statics'\'')|g" /code/app/dashboard/__init__.py\n\
chmod -R 755 /code/app/dashboard/build\n\
echo "Init.py updated, starting app..."\n\
cat /code/app/dashboard/__init__.py\n\
' > /code/debug.sh && chmod +x /code/debug.sh

# Create a start script to ensure migrations run correctly
RUN echo '#!/bin/bash\n\
/code/debug.sh\n\
echo "Running database migrations..."\n\
alembic upgrade head\n\
echo "Starting Marzban..."\n\
python main.py' > /code/start.sh && chmod +x /code/start.sh

CMD ["/code/start.sh"]
