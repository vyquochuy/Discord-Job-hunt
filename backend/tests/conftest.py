import pytest
from app.core.limiter import limiter


@pytest.fixture(autouse=True)
def disable_rate_limiter_in_tests():
    """
    Tự động tạm thời vô hiệu hóa rate limiter trong các bài test đơn vị/tích hợp
    để tránh bị nghẽn 429 khi chạy hàng trăm request liên tục trong vài giây.
    """
    original_state = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = original_state
