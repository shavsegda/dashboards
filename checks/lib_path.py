# -*- coding: utf-8 -*-
"""Один импорт вместо возни с путями: проверки запускаются из любой папки."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
