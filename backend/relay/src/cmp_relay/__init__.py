"""The public-ingress relay: how a request from the public website on AWS reaches
the application inside a network that accepts no incoming connection.

Two processes and a queue between them.

* The **bridge** runs beside the public portal on AWS. The portal's `/api`
  rewrite points at it. It turns each HTTP request into a sealed message on the
  request queue, waits for the sealed reply on its own reply queue, and answers
  the browser.
* The **collector** runs inside. It keeps asking the request queue for work - an
  outgoing HTTPS call, the only kind the network allows - checks each request
  against the allow-list and its deadline, calls the API, and posts the sealed
  reply back.

Nothing on AWS knows an inside address, and every connection across the
boundary is opened from inside. Bodies too large for a message travel through a
short-lived object in S3, sealed the same way.

The modules:

* `sealing` - what makes the queue and the bucket hold only ciphertext;
* `envelope` - the request and reply as they travel;
* `allowlist` - the routes, headers and cookies that may cross, and the input
  rule that keeps sealed values from being smuggled in;
* `config` - every setting, read from the environment;
* `transport` - the SQS and S3 calls both sides share;
* `bridge`, `collector` - the two processes;
* `keys`, `provision` - command-line helpers.
"""

__version__ = "0.1.0"
