FROM amd64/python:3.9.4-slim-buster

LABEL maintainers="dougbarry"

ENV PYTHONPATH /app/

WORKDIR /app

COPY /setup.py /m365digester-cli README.md /app/

COPY /m365digester/ /app/m365digester

RUN pip install --no-cache-dir .

ENTRYPOINT ["m365digester-cli"]