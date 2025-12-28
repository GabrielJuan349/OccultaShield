FROM python:3.13-slim

# Install uv using the official installer or image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /code

# Copy the entire backend directory (build context is ../backend)
COPY . .

# Install dependencies using uv and pyproject.toml
# uv supports reading dependencies directly from pyproject.toml
RUN uv pip install --system -r app/pyproject.toml

EXPOSE 8900

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8900"]
