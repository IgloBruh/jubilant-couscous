@echo off
set "PYTHONPATH=%~dp0src"
python -m depviz %*
