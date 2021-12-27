FROM ubuntu
#FROM public.ecr.aws/lambda/python:2.7

RUN echo "python"
RUN echo "install python"
RUN apt-get update
RUN apt-get install -y python

RUN mkdir app
WORKDIR /app
COPY . .
RUN chmod +x deploy.sh
RUN chmod +x start.sh