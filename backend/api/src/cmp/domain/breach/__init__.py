"""Personal data breaches - s.8(6) of the DPDP Act, Rule 7, and CERT-In.

The platform is the system of record for a breach: it records what happened,
tracks every duty's clock and holds the evidence of each duty done. People
contain the breach, make the determination, and submit to the Board and to
CERT-In through the regulators' own channels; the platform never talks to a
regulator.

Three modules, layered the way the rest of the domain is:

* `clock` - which duty falls due when, and how a duty's state is read from its
  events. Pure.
* `state_machine` - open and closed, and what blocks closing. Pure.
* `service` - the only writer. Every change goes through here so the audit row
  and the change share one transaction.
"""
