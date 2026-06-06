import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from analysis.services.knowledge_base_importer import import_knowledge_base


def main():
    summary = import_knowledge_base()
    for key, value in summary.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
