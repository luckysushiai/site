# HIDDEN_VERIFIER_ONLY
def split_bill(total_cents, people):
    if people <= 0:
        raise ValueError("people must be positive")
    base, extra = divmod(total_cents, people)
    shares = []
    index = 0
    while index < people:
        shares.append(base + (1 if index < extra else 0))
        index += 1
    return shares
