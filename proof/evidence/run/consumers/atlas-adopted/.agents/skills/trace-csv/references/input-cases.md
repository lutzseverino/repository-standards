# Choose the smallest revealing CSV

For delimiter handling, compare a normal comma-separated row with a quoted
field containing a comma. For numeric conversion, compare an ordinary number
with an empty field and a non-numeric token. For row handling, compare a header
plus one row with a header alone. Select cases relevant to the requested change;
record current behavior before deciding whether it should change.
