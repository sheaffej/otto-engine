FROM python:3.7

RUN pip install pytest pytest-cov coveralls setuptools

ADD requirements.txt /app/
WORKDIR /app
RUN pip install -r requirements.txt

ADD . /app
RUN pip install -e /app
RUN mkdir /config /json_rules

ENV PYTEST_ADDOPTS "--color=yes"
EXPOSE 5000/tcp

CMD [ "python", "./run_otto.py" ]
