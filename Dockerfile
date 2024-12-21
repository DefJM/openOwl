# Use the official Python image from the Docker Hub
FROM python:3.12.8-bullseye

# Set the working directory in the container
WORKDIR /app

# poetry
RUN pip install poetry

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false && \
    poetry install --no-root

# Copy the rest of the application code
COPY . .

# Set the user to non-root
RUN useradd -m myuser
USER myuser
