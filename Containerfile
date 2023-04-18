FROM registry.access.redhat.com/ubi8/ubi-minimal

USER 0
RUN microdnf install --nodocs -y --disableplugin=subscription-manager gcc libpq-devel python39 python39-devel
RUN pip3 install --no-cache-dir -U pip setuptools setuptools_scm wheel

WORKDIR /watney
COPY requirements.txt /watney/requirements.txt
RUN pip3 install --no-cache-dir --upgrade -r /watney/requirements.txt

COPY ./watney /watney/watney

USER 1001

# on running'
CMD ["uvicorn", "watney.main:app", "--host", "0.0.0.0", "--port", "80"]

