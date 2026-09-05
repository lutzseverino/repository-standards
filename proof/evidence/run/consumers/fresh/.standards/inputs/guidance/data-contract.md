# Keep the input contract discoverable

The CSV summarizer records its transport assumptions in `.csv-summary.json`
and explains those same assumptions in `docs/data-contract.md`: UTF-8 text,
comma delimiter, and a header row. This concern owns those three configuration
fields and that document. The publisher's fix preserves unrelated configuration
keys. Numeric conversion and error handling remain the consumer's behavior;
these transport declarations do not claim additional application features.
