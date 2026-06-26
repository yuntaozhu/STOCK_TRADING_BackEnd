import re

def clean_code(code: str) -> str:
    """
    Cleans stock tickers of prefixes/suffixes, returning a standard 6-digit string.
    e.g., 'sh600519' -> '600519', '000001.SZ' -> '000001'
    """
    # Remove SH, SZ, BJ prefixes/suffixes
    cleaned = re.sub(r'(?i)^[a-z]{2}|^[0-9]{6}\.[a-z]{2}$', '', code.strip())
    # Extract only the 6 digits if it is a dotted notation or other forms
    matches = re.search(r'\d{6}', code)
    if matches:
        return matches.group(0)
    return cleaned

def get_prefix(code: str) -> str:
    """
    Returns the market prefix for a 6-digit stock code: sh, sz, or bj.
    """
    cleaned = clean_code(code)
    if cleaned.startswith(("6", "9")):
        return "sh"
    elif cleaned.startswith("8") or cleaned.startswith("4"):
        return "bj"
    else:
        return "sz"
