# conftest.py
# Racine du depot : garantit que les modules applicatifs (app, billing,
# routes_billing, models_billing) sont importables par pytest quel que soit le
# repertoire depuis lequel la commande est lancee (CI ou poste local).
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
