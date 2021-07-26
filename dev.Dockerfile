FROM python:3.8

WORKDIR /app
COPY ./requirements.txt /app

RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python", "repeater.py"]