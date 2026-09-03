import pytest
from app.services.extraction.url_fetcher import is_safe_public_url
from app.services.tailoring.latex_compiler import LaTeXCompiler


def test_ssrf_protection_loopback():
    """Kiểm tra URLFetcher chặn dải loopback 127.0.0.1 và localhost."""
    is_safe, err = is_safe_public_url("http://127.0.0.1:8000/api/v1/system/purge-database")
    assert not is_safe
    assert "SSRF" in (err or "")

    is_safe, err = is_safe_public_url("http://localhost:8000/health")
    assert not is_safe
    assert "SSRF" in (err or "")


def test_ssrf_protection_cloud_metadata():
    """Kiểm tra URLFetcher chặn địa chỉ IP Cloud Metadata (169.254.169.254)."""
    is_safe, err = is_safe_public_url("http://169.254.169.254/latest/meta-data/")
    assert not is_safe
    assert "SSRF" in (err or "")


def test_ssrf_protection_private_ranges():
    """Kiểm tra URLFetcher chặn các dải RFC 1918 Private IPs (10.0.0.0/8, 192.168.0.0/16)."""
    is_safe, err = is_safe_public_url("http://10.0.0.1/admin")
    assert not is_safe
    assert "SSRF" in (err or "")

    is_safe, err = is_safe_public_url("http://192.168.1.1/")
    assert not is_safe
    assert "SSRF" in (err or "")


def test_ssrf_protection_invalid_scheme():
    """Kiểm tra URLFetcher chặn giao thức không phải http/https (file://, ftp://, gopher://)."""
    is_safe, err = is_safe_public_url("file:///etc/passwd")
    assert not is_safe
    assert err == "INVALID_URL_SCHEME"

    is_safe, err = is_safe_public_url("ftp://example.com/file")
    assert not is_safe
    assert err == "INVALID_URL_SCHEME"


def test_ssrf_allows_legitimate_public_url():
    """Kiểm tra URLFetcher cho phép các tên miền public hợp lệ."""
    # google.com or example.com
    is_safe, err = is_safe_public_url("https://example.com/job-posting")
    assert is_safe
    assert err is None


def test_latex_compiler_includes_no_shell_escape():
    """Kiểm tra lệnh gọi LaTeX Compiler luôn chứa flag '-no-shell-escape' để sandbox."""
    import inspect
    source = inspect.getsource(LaTeXCompiler.compile_tex)
    assert "-no-shell-escape" in source
