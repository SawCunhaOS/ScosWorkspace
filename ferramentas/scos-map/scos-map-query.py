#!/usr/bin/env python3
"""Entry fino do scos-map-query: consulta compacta sobre .scos-map/ (so leitura)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scos_map_query.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
