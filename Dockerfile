FROM python:2.7

RUN apt-get update -y

echo "Installing python dependencies"
RUN apt-get install -y python-pip python-dev