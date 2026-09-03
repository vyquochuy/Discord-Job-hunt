from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared Rate Limiter instance across Backend application
limiter = Limiter(key_func=get_remote_address)
