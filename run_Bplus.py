"""run_Bplus.py - condition B+: identical to B plus the prose schema documentation C receives.

Isolates "knowing the schema" from "having a formal ontology".
Run: python run_Bplus.py --size 20 --split dev [--dry-run]
"""
from run_B import main

if __name__ == "__main__":
    main("Bplus", with_schema=True)
