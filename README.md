# PayOps for Hermes

A native, read-only Hermes Agent plugin located in the `payops/` plugin directory for inspecting Paystack and Flutterwave transactions and producing deterministic reconciliation reports.

## Scope

PayOps exposes two tools:

- `payops_list_transactions`: list normalized provider transactions for an inclusive date range.
- `payops_reconcile`: summarize transactions and settlements separately, and report deterministic data-quality exceptions.

The plugin does not initiate charges, transfers, refunds, reversals, payouts, or any other account mutation. It has no hosted backend, database, dashboard, or frontend. Hermes provides the agent interface.

## Requirements

- Hermes Agent with native plugin support.
- Python 3.10 or newer.
- Provider API credentials. Use test credentials while developing.

## Configure

Configure these secrets in Hermes secret storage:

- `PAYSTACK_SECRET_KEY`
- `FLUTTERWAVE_SECRET_KEY`

Credentials are read through Hermes `agent.secret_scope.get_secret`. The plugin does not read a project `.env` file or print credentials.

## Tools

Both tools accept:

- `from_date`: inclusive ISO date, `YYYY-MM-DD`.
- `to_date`: inclusive ISO date, `YYYY-MM-DD`.
- `providers`: optional list containing `paystack`, `flutterwave`, or both. Defaults to both.
- `max_pages`: optional page cap from 1 to 20; defaults to 5.

Provider API calls are HTTPS GET requests only. Responses are capped at 5 MB and requests time out after 20 seconds.

## Reconciliation semantics and limitations

- Paystack transaction amounts are already expressed in minor units.
- Flutterwave transaction and settlement amounts are converted from major units to minor units using currency-specific precision (including zero- and three-decimal currencies).
- Duplicate references are detected within a provider only.
- Transaction totals and settlement totals are reported separately. They are not treated as directly equivalent because settlement timing can lag.
- Flutterwave v3 transaction listing uses successful and failed status filters; pending or in-progress transactions may not be returned.
- This report is not a substitute for bank-statement reconciliation or a merchant order ledger.

## Development

Run tests with:

```bash
python -m pytest -q
```

Validate with the Hermes CLI:

```bash
hermes plugins doctor payops/ --ci
hermes plugins validate payops/ --install-deps
```

## Security boundaries

- Read-only provider endpoints.
- HTTPS and explicit provider-host allowlist.
- No shell execution, subprocesses, arbitrary URLs, or user-controlled request hosts.
- Secrets are obtained from Hermes secret storage.
- Provider error messages are bounded and do not include response bodies or request headers.

## Status

Early MVP. Provider API response shapes and Hermes runtime compatibility must be verified against the target Hermes version before catalogue submission. Do not use production credentials until validation is complete.

## License

MIT
