#!/bin/bash
export $(grep -v '^#' .env.dev | xargs)
export APP_ENV=development
python -m server
