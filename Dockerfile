FROM ubuntu:latest
LABEL authors="sallo"

ENTRYPOINT ["top", "-b"]