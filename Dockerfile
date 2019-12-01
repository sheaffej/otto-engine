FROM python:3.7

RUN pip install pytest pytest-cov setuptools

ADD . /app
WORKDIR /app
RUN pip install -r requirements.txt

# WORKDIR /app/ottoengine
RUN pip install .

CMD [ "python", "./run_otto.py" ]
