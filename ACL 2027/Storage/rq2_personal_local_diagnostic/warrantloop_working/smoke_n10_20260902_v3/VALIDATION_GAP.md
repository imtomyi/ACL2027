# Validation gap record

This run is retained as an append-only engineering record but is superseded for
readiness decisions. The packet-level route function had no truth argument and
did not read truth, but the higher-level application function received a broad
input container that also held the smoke-test truth map. That unused field
violated the stronger requirement that inference cannot receive truth at all.

No manuscript or formal-experiment claim may use this run. The v4 successor uses
an answer-key-independent hash split, passes only train and validation truth to
the fitter, gives the application stage explicit projection-only arguments, and
loads the smoke-test truth subset only after the complete route file exists.
