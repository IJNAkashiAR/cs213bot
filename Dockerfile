FROM python:3.9.18
COPY ./requirements.txt .
RUN pip3 install -r requirements.txt
COPY . .
CMD [ "python3", "cs213bot.py" ]
