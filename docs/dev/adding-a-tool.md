# Adding a tool

1. Write the function in the module's `tools.py` with type hints and a one-line docstring.
2. Add a `[[tools]]` table to the module's `hal-module.toml`: `name`, `function`, `description`,
   `tier`, the effects (`reviewable`, `reversible`, `untrusted_output`, `network`) and typed
   `[[tools.params]]`. A path parameter needs `format = "path"` and an `access`; a parameter that
   carries a message body or file content needs `content = true`.
3. Add the row to `tests/tool-policy.csv`.
4. Write the tests, including one that fails without your change.
5. Run the checks in [Testing](testing.md), then commit code, tests and docs together.

| Symptom | Fix |
| --- | --- |
| Manifest test fails on a path parameter | Declare `format = "path"` and `access`. |
| Policy table test fails | Add or update the CSV row to match the manifest. |
| Timeout scan fails | Pass `timeout=` to the subprocess or network call. |
