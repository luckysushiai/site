def page(items, page_number, page_size):
    if page_number < 1:
        raise ValueError("page_number must be >= 1")
    if page_size < 1:
        raise ValueError("page_size must be >= 1")
    start = (page_number - 1) * page_size
    end = start + page_size + 1
    return list(items[start:end])
