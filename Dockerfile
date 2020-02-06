FROM python:3.8
ARG HOME_DIRECTORY='/home/ubuntu'
WORKDIR ${HOME_DIRECTORY}
COPY jobfunnel ${HOME_DIRECTORY}/
RUN apt-get update && apt-get install -y zip
RUN bash build.sh
RUN ls
RUN pwd
CMD ["bash"]
