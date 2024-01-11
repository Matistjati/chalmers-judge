#!/usr/bin/env bash
set -v

base_path=`dirname -- "$0"`/..

(cd $base_path && poetry run mypy omogenjudge)
