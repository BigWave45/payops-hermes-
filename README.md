# PayOps for Hermes

PayOps is a native, read-only Hermes Agent plugin for inspecting Paystack and Flutterwave transactions and producing deterministic reconciliation reports.

## Scope

PayOps exposes two tools:

- `payops_list_transactions`: list normalized provider transactions for an inclusive date range.
- `payops_reconcile`: summarize transactions and settlements separately and report deterministic data-quality exceptions.

The plugin does not initiate charges, transfers, refunds, reversals, payouts, or any other account mutation. It has no hosted backend, database, dashboard, or frontend.

## Requirements

- Python 3.10 or newer.
- Hermes Agent with the `client_credentials` plugin OAuth support from [this Hermes fork branch](https://github.com/BigWave45/hermes-agent/tree/feat/plugin-oauth-client-credentials). The feature is not yet part of the upstream Hermes release. The manifest's compatibility floor alone does not provide this capability.
- Provider credentials for the intended environment. Use test credentials during development.

## Configure

Configure these values in Hermes secret storage:

- `PAYSTACK_SECRET_KEY`: Paystack secret API key.
- `FLUTTERWAVE_CLIENT_ID`: Flutterwave v4 OAuth client ID.
- `FLUTTERWAVE_CLIENT_SECRET`: Flutterwave v4 OAuth client secret.

Flutterwave uses OAuth 2.0 `client_credentials`. After installing PayOps into the Hermes profile, authorize its declared client once:

```bash
hermes auth add payops:flutterwave
```

Hermes obtains the token from Flutterwave, stores it in the profile, refreshes it before expiry, and attaches it to API requests. PayOps does not read the client secret, acquire tokens, store bearer tokens, or receive bearer tokens in plugin code. The credentials must belong to the same Flutterwave environment as the API host.

Flutterwave v4 test mode uses `https://developersandbox-api.flutterwave.com`. Production uses `https://f4bexperience.flutterwave.com`. The adapter defaults to sandbox. Production selection must be an explicit code/configuration change; do not point test credentials at production.

## Tools

Both tools accept:

- `from_date`: inclusive ISO date, `YYYY-MM-DD`.
- `to_date`: inclusive ISO date, `YYYY-MM-DD`.
- `providers`: optional list containing `paystack`, `flutterwave`, or both. Defaults to both.
- `max_pages`: optional page cap from 1 to 20; defaults to 5.

Provider data requests are HTTPS GET requests only. PayOps uses Hermes' credentialed provider request helper for Flutterwave v4; Paystack continues to use Hermes secret storage and its existing HTTPS client. Requests time out after 20 seconds. Flutterwave API redirects are not followed by Hermes.

## Provider semantics and limitations

- Paystack transaction and settlement amounts are already expressed in minor units.
- Flutterwave v4 charge and settlement amounts are expressed in major units and are converted to minor units using currency-specific precision.
- Flutterwave v4 charge listing includes `succeeded`, `pending`, `failed`, and `voided` statuses.
- Flutterwave v4 list endpoints use page metadata. The `max_pages` limit is a deliberate safety bound; if more pages exist, the tool returns an explicit `provider_warnings` entry.
- Flutterwave v4 settlements are available only for live/production transactions. Sandbox settlement results cannot validate settlement reconciliation. Do not use production credentials merely to make this test pass.
- Duplicate references are detected within a provider only.
- Transaction totals and settlement totals are reported separately. They are not treated as directly equivalent because settlement timing can lag.
- This report is not a substitute for bank-statement reconciliation or a merchant order ledger.

## Development and validation

Provider adapter tests use mocked API responses. They verify normalization, status coverage, pagination, and use of the Hermes credentialed request interface. They do not prove that the user's Flutterwave credentials work or that the account contains matching data.

Run unit tests with:

```bash
python -m pytest -q
```

Validate the plugin using the Hermes fork build that contains client-credentials support:

```bash
hermes plugins doctor payops/ --ci
hermes plugins validate payops/ --install-deps
```

For a live sandbox test, install the plugin into that Hermes profile, configure the Flutterwave v4 test Client ID and Client Secret, run `hermes auth add payops:flutterwave`, and invoke `payops_list_transactions` with `providers: ["flutterwave"]`. This checks OAuth and read-only charge listing. Settlement retrieval must be tested against an approved live account; do not use production credentials just for a smoke test.

## Security boundaries

- PayOps only uses read-only provider endpoints.
- Flutterwave bearer credentials are attached by Hermes and are not returned to plugin code.
- Flutterwave API origins are restricted in the plugin manifest to the documented sandbox and production hosts.
- Hermes token requests use the declared OAuth token URL. PayOps never sends its client secret to the API host.
- Paystack API requests retain the existing host allowlist, disabled redirects, 5 MB response cap, and 20-second timeout.
- Provider error messages are bounded; response bodies and request headers are not included in raised errors.
- PayOps does not execute shell commands, spawn subprocesses, run background jobs, or send telemetry.

## Status

Flutterwave v4 OAuth integration is under validation on a feature branch. Do not treat this branch as a catalogue-ready release until the Hermes feature is merged upstream or an accepted release containing it is available, and the real Flutterwave sandbox test has passed.

## License

MIT
