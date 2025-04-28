# Use an official Python runtime as a parent image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set the working directory in the container
WORKDIR /app
RUN pip install uv 
# Copy the requirements file into the container at /app
COPY pyproject.toml .
COPY src/ src/ 
COPY ui.py .
# Install any needed packages specified in requirements.txt
RUN uv sync

# Copy the current directory contents into the container at /app
RUN uv pip install -e .

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Run app.py when the container launches
CMD ["uv", "run", "streamlit", "run", "--server.address=0.0.0.0", "--server.port=8501", "ui.py"]