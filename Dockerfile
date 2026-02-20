FROM python:3.10
WORKDIR /usr/src/app/
ADD requirements.txt /usr/src/app/
RUN pip install -r requirements.txt
RUN pip install fastapi
RUN pip install uvicorn
RUN apt update

RUN apt install -y iputils-ping net-tools vim

COPY main.py /usr/src/app/
CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8080"]