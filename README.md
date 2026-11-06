# PayOps for Hermes

A native, read-only Hermes Agent plugin located in the `payops/` plugin directory for inspecting Paystack and Flutterwave transactions and producing deterministic reconciliation reports.

## Scope

PayOps exposes two tools:

- `payops_list_transactions`: list normalized provider transactions for an inclusive date range.
- `payops_reconcile`: summarize transactions and settlements separately, and report deterministic data-quality exceptions.

The plugin does not initiate charges, transfers, refunds, reversals, payouts, or any other account mutation. It has no hosted backend, database, dashboard, or frontend. Hermes provides the agent interface.

## Requirements

- Hermes Agent 0.23.0 or newer (0.23.0 is the version currently used for compatibility testing).
- Python 3.10 or newer.
- Provider API credentials. Use test credentials while developing.

## Configure

Configure these secrets in Hermes secret storage:

- `PAYSTACK_SECRET_KEY`
- `FLUTTERWAVE_SECRET_KEY`

Credentials are read through Hermes `agent.secret_scope.get_secret`. Flutterwave v3 uses a static secret API key read from Hermes secret storage. PayOps does not perform OAuth token acquisition or refresh. The plugin does not read a project `.env` file or print credentials.

## Tools

Both tools accept:

- `from_date`: inclusive ISO date, `YYYY-MM-DD`.
- `to_date`: inclusive ISO date, `YYYY-MM-DD`.
- `providers`: optional list containing `paystack`, `flutterwave`, or both. Defaults to both.
- `max_pages`: optional page cap from 1 to 20; defaults to 5.

Provider API calls are HTTPS GET requests only. Provider data calls are read-only. Responses are capped at 5 MB and requests time out after 20 seconds.

## Reconciliation semantics and limitations

- Paystack transaction amounts are already expressed in minor units.
- Flutterwave v3 transaction amounts and settlement amounts are converted from major units to minor units using currency-specific precision (including zero- and three-decimal currencies).
- Duplicate references are detected within a provider only.
- Transaction totals and settlement totals are reported separately. They are not treated as directly equivalent because settlement timing can lag.
- Flutterwave v3 transactions are retrieved from the read-only transaction-list endpoint. The adapter requests successful and failed statuses. Pending transactions are not included by this endpoint.
- Both adapters follow provider pagination metadata. The `max_pages` limit is a deliberate safety bound; if more pages exist, the tool returns an explicit `provider_warnings` entry instead of silently presenting the result as complete.
- This report is not a substitute for bank-statement reconciliation or a merchant order ledger.

## Roadmap

The following are planned extensions, not features available in the current MVP. They are listed to make the intended direction explicit; inclusion here does not imply an implementation commitment or release date.

- **Merchant-reference matching:** compare provider transactions against a shared merchant order or payment reference when that reference is available and reliable.
- **Cross-provider matching:** identify likely corresponding Paystack and Flutterwave payments using shared merchant references. PayOps will not infer that two payments are duplicates merely because their amounts or timestamps are similar.
- **CSV exports:** provide downloadable, machine-readable transaction and reconciliation reports.
- **Scheduled reconciliation:** support recurring checks through Hermes scheduling or another supported Hermes execution mechanism, with new exceptions surfaced to the operator.
- **Historical reports:** compare reconciliation results over time. This may require an optional persistence layer; the current plugin does not maintain a database or store report history.

The roadmap is deliberately focused on improving reconciliation quality and operational visibility while preserving the current read-only boundary. Automated refunds, payouts, transfers, and other payment mutations are outside the current product scope.

## Development

Provider adapter tests use mocked API responses; they verify normalization and pagination behavior but do not replace live test-key verification.

For live, read-only provider verification, add these GitHub Actions repository secrets:

- `PAYSTACK_TEST_SECRET_KEY`
- `FLUTTERWAVE_TEST_SECRET_KEY`

Then run **Actions → Live provider smoke test → Run workflow** and select the provider(s) to check. The workflow reads a 14-day window, caps each endpoint at two pages, and prints only record counts and pagination warnings. It does not print transaction details or credentials. Do not add production credentials.

Run tests with:

```bash
python -m pytest -q
```

The plugin manifest declares `requires_hermes: ">=0.23.0"`. The catalogue entry must declare the same floor and pin the exact reviewed commit.

Validate with the Hermes CLI:

```bash
hermes plugins doctor payops/ --ci
hermes plugins validate payops/ --install-deps
```

## Security boundaries and disclosures

- PayOps makes HTTPS requests to Paystack and Flutterwave to retrieve transaction and settlement data. Flutterwave uses its v3 API with a static secret key supplied through Hermes secret storage.
- Provider data requests use read-only endpoints. PayOps does not initiate charges, transfers, refunds, reversals, payouts, or other payment mutations.
- Requests are restricted to an explicit provider-host allowlist, redirects are disabled, responses are capped at 5 MB, and requests time out after 20 seconds.
- API credentials are read through Hermes secret storage. PayOps does not read project `.env` files or other credential stores.
- Flutterwave API requests use the configured v3 secret key directly. No OAuth access token is acquired or stored.
- PayOps does not execute shell commands, spawn subprocesses, run background jobs, or send telemetry.
- Provider error messages are bounded; response bodies and request headers are not included in raised errors.

## Catalogue readiness

PayOps is not ready for Hermes catalogue submission yet. The Flutterwave integration now uses the v3 API with a static secret key read from Hermes secret storage. It does not independently acquire or refresh OAuth tokens. This removes the specific Rule 11 conflict identified in the previous v4 implementation.

A feature request has been opened with Hermes to add Hermes-managed `client_credentials` support: https://github.com/NousResearch/hermes-agent/issues/149975. Until Hermes provides a supported route or maintainers confirm an acceptable alternative, do not submit PayOps to the catalogue.

## Status

Early MVP. Automated tests, Hermes compatibility checks, and live provider smoke tests have passed. The latest live smoke test authenticated against both providers but returned zero transactions and zero settlements, so it confirms connectivity and authentication, not reconciliation against populated provider data. Do not use production credentials until validation is complete.

## License

MIT
