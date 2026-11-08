"""PayOps native Hermes plugin entry point."""
from functools import partial

from .schemas import LIST_TRANSACTIONS_SCHEMA, RECONCILE_SCHEMA
from .tools import list_transactions, reconcile


def register(ctx):
    """Register PayOps tools with the Hermes plugin runtime."""
    environment = ctx.get_config("flutterwave_environment", default="sandbox")
    if environment not in ("sandbox", "production"):
        raise ValueError("flutterwave_environment must be sandbox or production")

    ctx.register_tool(
        name="payops_list_transactions",
        toolset="payops",
        schema=LIST_TRANSACTIONS_SCHEMA,
        handler=partial(list_transactions, flutterwave_environment=environment),
    )
    ctx.register_tool(
        name="payops_reconcile",
        toolset="payops",
        schema=RECONCILE_SCHEMA,
        handler=partial(reconcile, flutterwave_environment=environment),
    )
