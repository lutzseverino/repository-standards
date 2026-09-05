# Ledger totals

Run this example from the repository root with Python 3 (standard library only):

```sh
cat > /tmp/ledger-example.csv <<'CSV'
item,amount
"Service, monthly",12.50
Refund,-2
CSV
python3 app.py /tmp/ledger-example.csv amount
```

Observed output:

```json
{"column": "amount", "count": 2, "total": 10.5}
```

This is an internal helper for the Wednesday reconciliation. Finance keeps the
input exports locally; the repository contains no customer data. The example
above uses synthetic rows.

The interface is `python3 app.py FILE COLUMN`; `python3 app.py --help` shows
usage. Input is UTF-8 CSV with commas and a header row; quoted commas are
supported. See [the transport contract](docs/data-contract.md) and
[its configuration](.csv-summary.json). The script implements these assumptions
directly; it does not read the configuration file.

Each selected value is converted with Python's `float()` and summed. Empty,
missing, or non-numeric selected values abort the command without a JSON result;
rows are not silently skipped. Unknown columns and file-reading errors also
produce an argparse error on stderr and exit status 2. A header alone with the
requested column produces count 0 and total 0. Conversion uses floating-point
arithmetic, with its usual precision limits, and accepts `nan` and `inf`.

For example, this invalid input:

```sh
cat > /tmp/ledger-invalid.csv <<'CSV'
item,amount
Service,oops
CSV
python3 app.py /tmp/ledger-invalid.csv amount
```

produces no stdout, exits with status 2, and writes:

```text
usage: app.py [-h] file column
app.py: error: could not convert string to float: 'oops'
```

**Working here:** Follow the existing employer [CONTRIBUTING.md](CONTRIBUTING.md)
for internal review procedures. It requires two employee reviewers in the
company tracker and remains the authority for contributions.
