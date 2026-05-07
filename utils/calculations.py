VAT = 1.05

def round_to_50(value: float) -> float:
    """Round to nearest 50 with threshold at 35.
    Remainder < 35  → round down to lower 50.
    Remainder >= 35 → round up to next 50.
    """
    remainder = value % 50
    if remainder >= 35:
        return value + (50 - remainder)   # round up
    return value - remainder               # round down
STANDARD_MULTIPLIER  = 1.2 * VAT   # 1.26
EK_CUI_MULTIPLIER    = 0.75 * VAT  # 0.7875
STANDARD_DEPOSIT_MUL = 2.0

def calc_activation_amount(rent: float, category: str) -> float:
    if category in ('EK', 'Cuisinette'):
        return round(rent * EK_CUI_MULTIPLIER)
    return round(rent * STANDARD_MULTIPLIER)

def calc_deposit(rent: float, category: str, deposit_multiplier: float) -> float:
    mul = STANDARD_DEPOSIT_MUL if category == 'Standard' else deposit_multiplier
    return round(rent * mul)

def is_waived(license_type: str, manually_waived: bool) -> bool:
    return license_type == "DMCC TL" or manually_waived

def calc_total(deposit: float, activation_fee: float) -> float:
    return deposit + activation_fee
