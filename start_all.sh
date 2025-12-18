#!/usr/bin/env bash
set -e

usage() {
  echo "Usage: $0 [backend|frontend]"
  exit 1
}

if [ $# -ne 1 ]; then
  usage
fi

CMD=$1

case "$CMD" in
  backend)
    # run FastAPI backend
    uvicorn backend.main:app --reload
    ;;
  frontend)
    cd frontend
    npm run dev
    ;;
  *)
    usage
    ;;
esac
