def remove_prefix(string: str, prefix: str) -> str:
    """
    Remove a prefix from a string, if it exists.
    """
    if string.startswith(prefix):
        return string[len(prefix) :]
    return string
