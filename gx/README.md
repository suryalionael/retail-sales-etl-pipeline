# Great Expectations

The pipeline depends on Great Expectations and executes validation in `etl/validate.py` for:

- source schema validation
- required null checks
- duplicate checks on dimensions and fact business keys
- referential integrity before and after loading

Validation is code-first so the same checks run in local CLI, tests, and Airflow without committing generated validation stores.
