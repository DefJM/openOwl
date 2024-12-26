# Use the official Python image from the Docker Hub
FROM python:3.12.8-bullseye

# Set the working directory in the container
WORKDIR /app

RUN pip install poetry

# Configure poetry to create the virtual environment in the project directory
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

# Add poetry's bin directory to PATH
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root

# Set the user to non-root and ensure proper permissions
RUN useradd -m myuser && \
    chown -R myuser:myuser /app

USER myuser

# Copy the rest of the application code
COPY . .