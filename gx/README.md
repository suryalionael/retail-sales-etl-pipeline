# Great Expectations

The pipeline depends on Great Expectations in Docker/Airflow (`requirements-airflow.txt`) and executes validation in `etl/validate.py` for:

- source schema validation
- required null checks
- duplicate checks on dimensions and fact business keys
- referential integrity before loading

Validation logic is implemented in pandas so the same checks run in local CLI, unit tests, and CI without installing Great Expectations. The GE runtime is available in the Airflow container for future checkpoint expansion; `checkpoints/retail_sales.yml` documents the intended checkpoint name.
