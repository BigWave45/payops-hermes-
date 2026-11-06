"""PayOps native Hermes plugin entry point."""
from .schemas import LIST_TRANSACTIONS_SCHEMA, RECONCILE_SCHEMA
from .tools import list_transactions, reconcile

def register(ctx):
    """Register PayOps tools with the Hermes plugin runtime."""
    ctx.register_tool(
        name="payops_list_transactions",
        toolset="payops",
        schema=LIST_TRANSACTIONS_SCHEMA,
        handler=list_transactions,
    )
    ctx.register_tool(
        name="payops_reconcile",
        toolset="payops",
        schema=RECONCILE_SCHEMA,
        handler=reconcile,
    )
