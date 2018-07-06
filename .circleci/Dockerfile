ARG PYTHON_VERSION=3.6
FROM circleci/python:$PYTHON_VERSION

WORKDIR /home/circleci/app/
COPY . /home/circleci/app/
RUN sudo chown -R circleci:circleci .
RUN sudo pip install tox
