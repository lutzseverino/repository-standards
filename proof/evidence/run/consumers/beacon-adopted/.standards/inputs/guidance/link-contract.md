# Link inventory contract

Keep docs/link-policy.json and tests/fixtures/link-contract.md consistent. The
JSON expected_links array is the expected result of running app.py on the
fixture; it describes extraction only. An HTTPS URL in the fixture is literal
input, not permission to make a request. The declared repair writes this small
shared example to both files. The declared check compares the consumer's actual
JSON output with the policy and checks offline scope and the fixture path.

This concern has no single target file. It owns the policy/example relationship;
ordinary prose around the example remains repository-owned.
