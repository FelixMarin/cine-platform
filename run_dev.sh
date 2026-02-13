#!/bin/bash
export $(grep -v '^#' .env | xargs)
python -m server
