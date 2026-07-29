FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app
RUN groupadd --system app && useradd --system --gid app --create-home app
COPY --chown=app:app src ./src
COPY --chown=app:app config ./config
COPY --chown=app:app examples ./examples
USER app

ENTRYPOINT ["python", "-m", "control_plane", "--spec-dir", "examples/specs", "--policy", "config/policy.json"]
CMD ["validate"]

