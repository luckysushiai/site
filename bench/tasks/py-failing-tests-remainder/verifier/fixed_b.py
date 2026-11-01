# HIDDEN_VERIFIER_ONLY
def split_bill(total_cents, people):
    if people <= 0:
        raise ValueError("people must be positive")
    base, extra = divmod(total_cents, people)
    return [base + 1 if index < extra else base for index in range(people)]
