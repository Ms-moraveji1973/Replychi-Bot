FROM python:3.10-slim-buster

WORKDIR /app

COPY requirements.txt /app/

RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

COPY . /app/

CMD ["python", "main.py"]