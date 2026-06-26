import socket
import logging
from mootdx.quotes import Quotes

logger = logging.getLogger("a_stock.mootdx")

# Known active TongdaXin server nodes (verified for 2026)
_TDX_SERVERS = [
    ('119.97.185.59', 7709), 
    ('124.70.133.119', 7709), 
    ('116.205.183.150', 7709),
    ('123.60.73.44', 7709),  
    ('116.205.163.254', 7709), 
    ('121.36.225.169', 7709),
    ('123.60.70.228', 7709), 
    ('124.71.9.153', 7709),    
    ('110.41.147.114', 7709),
    ('124.71.187.122', 7709),
]

def _probe(ip: str, port: int, timeout: float = 1.5) -> bool:
    """
    Perform a quick TCP handshake to check if the server is alive and reachable.
    """
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False

def tdx_client(market: str = 'std'):
    """
    Creates a mootdx Quotes client, bypassing the mootdx 0.11.x config BESTIP bug.
    
    Checks our static active IP list first to find a responsive server, then
    falls back to mootdx's built-in speed test.
    """
    # 1. Search responsive servers in our known good list
    for ip, port in _TDX_SERVERS:
        if _probe(ip, port):
            try:
                logger.info(f"Connecting to verified TDX server: {ip}:{port}")
                return Quotes.factory(market=market, server=(ip, port))
            except Exception as e:
                logger.warning(f"Failed connecting to verified server {ip}:{port}: {e}")
                
    # 2. Fallback to mootdx speed testing
    try:
        logger.info("Falling back to mootdx automatic bestip determination")
        return Quotes.factory(market=market, bestip=True)
    except Exception as e:
        logger.warning(f"bestip fallback failed: {e}")
        
    # 3. Last resort fallback (mootdx default, might fail with BESTIP bug)
    try:
        logger.info("Falling back to standard mootdx Quotes factory")
        return Quotes.factory(market=market)
    except Exception as e:
        raise RuntimeError(
            f"All mootdx servers are unreachable. Overseas networks may block TCP 7709 port. "
            f"Please verify your connection or use proxies. Details: {e}"
        )
