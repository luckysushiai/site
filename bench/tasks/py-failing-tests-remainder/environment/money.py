def split_bill(total_cents, people):
    if people <= 0:
        raise ValueError("people must be positive")
    base = total_cents // people
    return [base] * people
