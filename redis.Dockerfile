# hadolint ignore=DL3006
FROM redis

CMD [ "redis-server", "--appendonly", "yes" ]