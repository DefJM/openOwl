# Use the official Python image from the Docker Hub
FROM python:3.12.8-bullseye

# Set the working directory in the container
WORKDIR /app

RUN pip install poetry

COPY . .

RUN poetry install