"""Rights requests - sections 11 to 14 of the DPDP Act.

A data principal may ask for access (s.11), correction or erasure (s.12), raise
a grievance (s.13), and nominate somebody to act for her (s.14). This package
is the record of the asking: when it arrived, how she was verified, what every
holder of her data was told to do, what was decided about each thing held, and
what she was told in reply - all against a clock that starts on receipt.

Three modules, layered the way the rest of the domain is:

* `clock` - the deadlines, computed from the receipt time and the published
  period. Pure.
* `state_machine` - which status may follow which, for whom, and what blocks
  it. Pure.
* `service` - the only writer. Every change to a request goes through here so
  the audit row and the change share one transaction.
"""
