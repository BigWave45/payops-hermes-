# PayOps for Hermes

PayOps is a native, read-only Hermes Agent plugin for inspecting Paystack and Flutterwave transactions and producing deterministic reconciliation reports.

## Scope

PayOps exposes two tools:

- `payops_list_transactions`: list normalized provider transactions for an inclusive date range.
- `payops_reconcile`: summarize transactions and settlements separately and report deterministic data-quality exceptions.

The plugin does not initiate charges, transfers, refunds, reversals, payouts, or any other account mutation. It has no hosted backend, database, dashboard, or frontend.

## Requirements

- Python 3.10 or newer.
- Hermes Agent with plugin-managed OAuth 2.0 `client_credentials` support. This capability is not yet available in the current upstream Hermes release, so the Flutterwave path in this development branch is not usable on a standard upstream installation yet.
- Provider credentials for the intended environment. Use test credentials during development.

For standard upstream Hermes installations, use the Paystack-only catalog release until the required OAuth support is released upstream.

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

## Install and use

PayOps runs inside Hermes Agent; it is not a standalone dashboard or hosted payment service. This dual-provider development branch is not the catalog installation path. On standard upstream Hermes installations, use the Paystack-only catalog release until Hermes releases the required OAuth capability.

When using a Hermes release that supports plugin-managed `client_credentials`, store provider credentials in Hermes secret storage, not in prompts or source files. For Flutterwave v4, add its OAuth client after installing the compatible PayOps release:

```bash
hermes auth add payops:flutterwave
```

Then ask the Hermes agent to use the PayOps tools. For example:

- "List my Flutterwave transactions from 1 October to 31 October 2026."
- "Reconcile my Paystack transactions and settlements for last month."
- "Compare transaction totals and settlement totals across Paystack and Flutterwave for this date range. Show exceptions."

The agent calls `payops_list_transactions` for transaction inspection and `payops_reconcile` for transaction/settlement summaries and deterministic data-quality exceptions. The date range is required. Specify a provider when you do not want both configured providers queried.

The current public implementation is a custom Git install, not yet a reviewed Hermes catalog listing. Its Flutterwave v4 path requires the Hermes OAuth feature proposed in [PR #150013](https://github.com/NousResearch/hermes-agent/pull/150013), so a standard upstream Hermes release cannot yet run that path without the feature.

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

Validate the dual-provider development branch against a Hermes build that supports plugin-managed `client_credentials`:

```bash
hermes plugins doctor payops/ --ci
hermes plugins validate payops/ --install-deps
```

For an automated sandbox test, add GitHub Actions repository secrets named `FLUTTERWAVE_CLIENT_ID` and `FLUTTERWAVE_CLIENT_SECRET`. The smoke workflow runs automatically when its workflow file or the Flutterwave adapter changes on `feat/flutterwave-v4-hermes-oauth`; it can also be started manually when GitHub exposes the workflow for that branch. The workflow creates an isolated Hermes profile, runs `hermes auth add payops:flutterwave`, and invokes the public `payops_list_transactions` tool against the sandbox without printing credentials or transaction details. It uses sandbox credentials only. Settlement retrieval must be tested against an approved live account; do not use production credentials just for a smoke test.

## Security boundaries

- PayOps only uses read-only provider endpoints.
- Flutterwave bearer credentials are attached by Hermes and are not returned to plugin code.
- Flutterwave API origins are restricted in the plugin manifest to the documented sandbox and production hosts.
- Hermes token requests use the declared OAuth token URL. PayOps never sends its client secret to the API host.
- Paystack API requests retain the existing host allowlist, disabled redirects, 5 MB response cap, and 20-second timeout.
- Provider error messages are bounded; response bodies and request headers are not included in raised errors.
- PayOps does not execute shell commands, spawn subprocesses, run background jobs, or send telemetry.

## Roadmap

The current release is deliberately a read-only foundation. The longer-term product direction is to become a payment-operations and financial-oversight layer for businesses and AI agents that initiate or manage commercial activity.

Potential next stages, subject to validation and demand:

1. **Continuous operations:** scheduled reconciliation, recurring reports, and alerts when new discrepancies or unusual payment patterns appear.
2. **Broader financial visibility:** additional payment providers, currencies, reporting periods, and exports for finance teams.
3. **Business-system reconciliation:** compare provider records with merchant orders, invoices, internal ledgers, and bank statements. This requires explicit connectors and matching rules; it is not part of the current plugin.
4. **Agent financial governance:** auditable visibility into agent-related spending and receipts, policy-aware review, and eventually controlled payment workflows with explicit authorization and safeguards.

The last stage is an ambition, not a current capability. PayOps currently performs read-only provider retrieval and deterministic comparison of provider transaction and settlement records. It does not yet monitor continuously, connect to merchant ledgers, detect fraud, or authorize or execute payments.

## Hermes contribution

PayOps exposed a missing capability in Hermes: plugins could use interactive OAuth authorization-code/PKCE, but could not declare machine-to-machine OAuth 2.0 `client_credentials` while keeping token handling inside Hermes. We submitted a proposal and implementation for that reusable capability in [Hermes PR #150013](https://github.com/NousResearch/hermes-agent/pull/150013), linked to [issue #149975](https://github.com/NousResearch/hermes-agent/issues/149975).

The focused Hermes OAuth tests pass, and PayOps provides a separate provider integration against Flutterwave v4 sandbox. This is a concrete plugin-side validation of the feature, not evidence of upstream acceptance. The PR remains a draft pending maintainer review.

## Status

The Flutterwave v4 sandbox OAuth and PayOps transaction-list handler smoke test passed. The sandbox returned zero transactions for the queried period, so the test proves authentication and read access, not reconciliation against populated account data. Flutterwave v4 sandbox does not provide settlement records for live transactions; settlement reconciliation still requires an approved live account with real records. Do not use production credentials merely to make a test pass.

Do not treat the current feature branch as a generally installable upstream-catalogue release until Hermes merges and releases the OAuth capability. The upstream-compatible catalog release currently supports Paystack only.

## License

MIT
