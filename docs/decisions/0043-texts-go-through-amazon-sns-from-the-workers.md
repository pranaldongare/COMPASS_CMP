# 0043. Texts go through Amazon SNS from the workers

**Status:** proposed · 2026-11-17. No migration. Narrows the review of
2026-09-10, which kept a provider SDK for SMS out because no provider had
been chosen.

## Context

The platform has sent texts only through the HTTP transport: a JSON POST to
a gateway, with a provider-specific adapter in front, so that no provider SDK
or credential lived in the platform. No provider had been chosen, and no
credentials existed.

The organisation has chosen Amazon SNS, first for a demo on the free tier, in
Mumbai, the Region the relay already uses. The platform server already
reaches AWS through the outbound proxy, and already holds AWS credentials for
the relay's collector. An adapter in front of SNS would be a second thing to
deploy and secure (a function behind a public address, with a token of its
own), and the message key that India's DLT template IDs need would have to
travel in its payload anyway.

## Decision

1. A fourth transport, `sns`, publishes each text straight to the phone
   number through SNS, as Transactional. `http`, `console` and `null` stay.
2. Credentials are the standard AWS chain of the worker's environment. None
   is a setting. For the demo, a key that can publish only to phone numbers,
   only from the organisation's egress address; before real users, IAM
   Roles Anywhere, as for the collector.
3. The proxy is `HTTPS_PROXY` and `NO_PROXY`, as for the API's calls to the
   organisation's sign-in. `sns.ap-south-1.amazonaws.com` is one more name
   on the proxy, with no TLS inspection.
4. A number stored without a country code gets `SMS_DEFAULT_COUNTRY_CODE`
   (91) on its way to SNS. Stored values do not change.
5. Production accepts `http` or `sns`.
6. Failures keep the HTTP transport's contract: passing trouble is a
   `ConnectionError` or `TimeoutError` and is retried; a refusal is a
   `RuntimeError` and is not.
7. The API carries botocore, not boto3. The workers make one call,
   `Publish`, and botocore is the whole of what boto3 would use for it;
   boto3 adds the S3 transfer manager and its resource layer, which nothing
   here needs. The credential chain, the proxy handling and the retries are
   botocore's either way.

## Consequences

- The API's requirements carry botocore and jmespath, at the relay's pins.
- "Delivered" in the platform means SNS accepted the text. Whether the phone
  got it is in SNS's delivery logs in CloudWatch.
- To India without DLT registration, texts go by the international route: a
  random numeric sender, priced per text, sometimes blocked by a carrier. Fit
  for a demo, not for real users.
- While the account is in the SNS sandbox, only verified numbers (up to 10)
  receive texts. A text to any other number is refused, logged
  `sms.gateway_refused` and not retried: on a demo database full of made-up
  mobiles that is most texts, and it is the sandbox doing its job.
- SNS's own words for a refusal can quote the phone number, so the platform
  logs its error code and never its message.
- A worker with no credentials logs `sms.not_configured` once per text and
  does not retry: the text is lost, as it would be with a wrong gateway
  token. `scripts/send_test_sms.py`, run in the worker's environment, is the
  check before anybody waits for a code.

## Revisit when

- The organisation is registered on DLT: the entity ID and a template ID per
  message then travel with each text, which needs the message's key at the
  transport.
- A second SMS provider is wanted: the HTTP transport and an adapter remain
  the way to add one.
- Texts must leave from somewhere other than the inside workers.
- Delivery receipts are wanted in the platform rather than in CloudWatch.
