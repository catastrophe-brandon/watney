FROM python:3.11

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -U pip setuptools setuptools_scm wheel

WORKDIR /watney
#COPY ops/scripts/docker_entrypoint.sh linknotfound/docker_entrypoint.sh
COPY requirements.txt /watney/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /watney/requirements.txt

COPY ./watney /watney/watney

# on running'
CMD ["uvicorn", "watney.main:app", "--host", "0.0.0.0", "--port", "80"]

