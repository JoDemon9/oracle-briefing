# -*- coding: utf-8 -*-
"""
Canonical .env loader for The Oracle Sovereign pipeline.
Real environment variables always win over .env file values.
"""

import os

def load_env(env_path=None):
    if env_path is None:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        env_path = os.path.join(base_dir, '.env')

    if not os.path.exists(env_path):
        return

    try:
        with open(env_path, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip().lstrip('\ufeff')
                v = v.strip().strip('\'"')
                os.environ.setdefault(k, v)  # Real environment variables win
    except Exception as e:
        print(f"Warning: could not read .env file: {e}")
