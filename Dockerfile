#FROM python:2.7
FROM public.ecr.aws/lambda/python:2.7

RUN echo "Installing python dependencies"
RUN apt-get install -y python-pip python-dev