def money(value: float) -> str:
    return f"{value:,.0f}" if abs(value) >= 1000 else f"{value:,.2f}"
