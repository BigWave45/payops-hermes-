# PayOps for Hermes

PayOps is a native, read-only Hermes Agent plugin for inspecting Paystack transactions and producing deterministic reconciliation reports.

## Scope

PayOps exposes two tools:

- `payops_list_transactions`: list normalized Paystack transactions for an inclusive date range.
- `payops_reconcile`: summarize Paystack transactions and settlements separately and report deterministic data-quality exceptions.

This catalog release supports Paystack only. It does not initiate charges, transfers, refunds, reversals, payouts, or any other account mutation. It has no hosted backend, database, dashboard, or frontend.

## Requirements

- Python 3.10 or newer.
- Hermes Agent `>=0.23.0`.
- A Paystack secret API key. Use a test key during development.

## Configure

Store `PAYSTACK_SECRET_KEY` in Hermes secret storage. Do not put credentials in prompts or source files.

## Install and use

Install PayOps from the Hermes plugin catalog, then enable it:

```bash
hermes plugins install payops
hermes plugins enable payops
```

Ask Hermes to use the PayOps tools. For example:

- "List my Paystack transactions from 1 October to 31 October 2026."
- "Reconcile my Paystack transactions and settlements for last month."
- "Show duplicate transaction references in this date range."

## Tool arguments

Both tools accept:

- `from_date`: inclusive ISO date, `YYYY-MM-DD`.
- `to_date`: inclusive ISO date, `YYYY-MM-DD`.
- `providers`: optional list; this catalog release accepts `paystack` only and defaults to it.
- `max_pages`: optional page cap from 1 to 20; defaults to 5.

Provider data requests use HTTPS GET only. Paystack amounts are already expressed in minor currency units. The page cap is a deliberate safety bound; if more pages exist, the provider adapter reports a warning.

## Reconciliation semantics and limitations

- Transaction totals and settlement totals are reported separately. They are not treated as directly equivalent because settlement timing can lag.
- Duplicate references are detected within the provider only.
- This report is not a substitute for bank-statement reconciliation or a merchant order ledger.
- Provider API availability and the account's own data determine whether a query returns records.

## Development and validation

Run unit tests with:

```bash
python -m pytest -q
```

Validate the plugin using Hermes:

```bash
hermes plugins doctor payops/ --ci
hermes plugins validate payops/ --install-deps
```

The repository's broader development line also contains a Flutterwave v4 integration. That integration is intentionally excluded from this catalog release because Hermes upstream does not yet support the required machine-to-machine OAuth grant. The separate development branch retains that work while the catalog build remains compatible with upstream Hermes.

## Roadmap

The current release is a read-only foundation. The longer-term direction is a payment-operations and financial-oversight layer for businesses and AI agents.

Potential future work includes scheduled reconciliation and discrepancy alerts, additional providers and currencies, matching provider records against merchant orders and internal ledgers, and agent-related financial oversight. These are roadmap items, not current capabilities. PayOps does not currently monitor continuously, connect to merchant ledgers, detect fraud, or authorize or execute payments.

## License

MIT
