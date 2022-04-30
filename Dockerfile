# set container runtime env
FROM python:3.8-slim
# set wd of container
WORKDIR /src
# copy files into container
COPY ./src /src
COPY ./artifacts /src
# install dependencies
RUN pip3 install -r requirements.txt
# env vars - ENV MESSAGE = "hello world"
# run cmds on container start
CMD ["python","/src/main.py"]
