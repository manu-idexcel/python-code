#FROM python:2.7
FROM python:2.7public.ecr.aws/lambda/python:latest

RUN apt-get update -y

RUN echo "Installing python dependencies"
RUN apt-get install -y python-pip python-dev