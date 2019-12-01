FROM python:3.7

RUN pip install pytest pytest-cov setuptools

ADD requirements.txt /app/
WORKDIR /app
RUN pip install -r requirements.txt

ADD . /app
# RUN pip install .
RUN pip install -e /app
RUN mkdir /config /json_rules

EXPOSE 5000/tcp
CMD [ "python", "./run_otto.py" ]
