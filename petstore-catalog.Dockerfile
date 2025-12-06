# hadolint ignore=DL3007
FROM petstore-env:latest AS env

HEALTHCHECK --interval=3s --timeout=2s --start-period=3s --retries=10 \
  CMD curl --fail http://localhost:$PETSTORE_PORT/ || exit 1

CMD ["uv", "run", "petstore-catalog"]
