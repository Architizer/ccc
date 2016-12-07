FROM python:3

ENV PYTHONUNBUFFERED 1
ADD . /code
WORKDIR /code
RUN pip install --upgrade pip
RUN pip install -r /code/requirements.txt
RUN pip install .
