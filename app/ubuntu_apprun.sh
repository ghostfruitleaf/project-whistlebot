#!/bin/bash
nohup hypercorn app:app --bind '0.0.0.0:8000' &
