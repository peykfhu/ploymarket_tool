
from datetime import datetime





def timestamp_now() -> str:

    return datetime.utcnow().isoformat()



def format_usd(amount: float) -> str:

    return f"${amount:,.2f}"



def format_percent(value: float) -> str:

    return f"{value:.2f}%"

