#!/usr/bin/env bash
set -e
set -v

sudo service omogenjudge-queue stop || true

sudo -u postgres psql omogenjudge -c "DELETE FROM submission;"

sudo service omogenjudge-queue start || true
