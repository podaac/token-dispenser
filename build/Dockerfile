FROM --platform=linux/amd64 python:3.12-alpine

RUN apk update && apk add zip bash 
VOLUME /dist
COPY build.sh /
ENTRYPOINT /bin/bash build.sh
