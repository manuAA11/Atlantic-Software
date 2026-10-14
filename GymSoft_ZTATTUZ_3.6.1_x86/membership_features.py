"""Representation helpers only; permissions, access and duration come from the server."""
def internal_plan(plan):
    return (plan or {}).get('plan_type') == 'INTERNAL'

def internal_membership(membership):
    return (membership or {}).get('membership_type') == 'INTERNAL'

def financial_membership(membership):
    return (not internal_membership(membership)
            and membership.get('include_in_financial_stats', True)
            and membership.get('payment_status', 'posted') == 'posted')

def expiry_label(membership, formatter):
    if membership.get('has_expiration', True) is False:
        return 'Sin vencimiento'
    return formatter(membership.get('membership_end') or membership.get('end_date'))
