import ipaddress
import json
import logging
import re
import socket
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("url_fetcher")


def is_safe_public_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Kiểm tra ngăn chặn tấn công SSRF (Server-Side Request Forgery).
    Chặn các địa chỉ nội bộ, loopback, private ranges, và cloud metadata endpoints.
    Trả về: (is_safe, error_message_hoặc_None)
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, "INVALID_URL_SCHEME"
        hostname = parsed.hostname
        if not hostname:
            return False, "INVALID_HOSTNAME"

        # Chặn các host đặc biệt và cloud metadata
        if hostname.lower() in ("localhost", "127.0.0.1", "::1", "metadata.google.internal", "169.254.169.254"):
            return False, "SSRF_BLOCKED: Cloud metadata or localhost endpoint"

        # Phân giải DNS kiểm tra IP
        ip_list = socket.getaddrinfo(hostname, None)
        for item in ip_list:
            ip_str = item[4][0]
            ip = ipaddress.ip_address(ip_str)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                return False, f"SSRF_BLOCKED: Resolved to private or loopback IP ({ip_str})"
        return True, None
    except Exception as e:
        return False, f"SSRF_BLOCKED: DNS resolution error: {str(e)}"


@dataclass
class FetchedDocument:
    url: str
    final_url: str
    status_code: int
    content_type: str
    html: Optional[str]
    title: Optional[str]
    meta_description: Optional[str]
    og_title: Optional[str]
    og_description: Optional[str]
    json_ld: Optional[Dict[str, Any]]
    clean_text: str
    fetch_method: str  # "httpx" | "browser" | "failed"
    error: Optional[str] = None


class URLFetcher:
    """
    Service chuyên biệt thu thập nội dung HTML từ URL bất kỳ,
    làm sạch mã nguồn và trả về cấu trúc FetchedDocument.
    """

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }

    # Minimum readable text length to consider the page having actual job content
    MIN_CONTENT_LENGTH = 80

    async def fetch(self, url: str, timeout: float = 15.0) -> FetchedDocument:
        """
        Fetch HTML from URL via HTTP client and parse into FetchedDocument.
        If page lacks content or appears to be a client-side JS app, flags with JS_REQUIRED.
        """
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            return FetchedDocument(
                url=url,
                final_url=url,
                status_code=0,
                content_type="",
                html=None,
                title=None,
                meta_description=None,
                og_title=None,
                og_description=None,
                json_ld=None,
                clean_text="",
                fetch_method="failed",
                error="INVALID_URL_SCHEME",
            )

        # Chặn SSRF
        is_safe, err_msg = is_safe_public_url(url)
        if not is_safe:
            return FetchedDocument(
                url=url,
                final_url=url,
                status_code=0,
                content_type="",
                html=None,
                title=None,
                meta_description=None,
                og_title=None,
                og_description=None,
                json_ld=None,
                clean_text="",
                fetch_method="failed",
                error=err_msg or "SSRF_BLOCKED: URL target resolves to private or unsafe address",
            )

        # 1. Chuyên biệt: VietnamWorks API lookup nếu URL chứa job ID
        if "vietnamworks.com" in url.lower():
            vnw_doc = await self._fetch_vietnamworks_api(url)
            if vnw_doc:
                return vnw_doc

        try:

            async def on_response(response: httpx.Response):
                if response.is_redirect:
                    next_url = response.headers.get("Location")
                    if next_url:
                        target_redirect = str(response.url.join(next_url))
                        safe, r_err = is_safe_public_url(target_redirect)
                        if not safe:
                            raise httpx.RequestError(f"Redirect to unsafe address blocked: {next_url} ({r_err})")

            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                headers=self.DEFAULT_HEADERS,
                event_hooks={"response": [on_response]},
            ) as client:
                response = await client.get(url)
                final_url = str(response.url)
                status_code = response.status_code
                content_type = response.headers.get("content-type", "")

                if status_code >= 400:
                    return FetchedDocument(
                        url=url,
                        final_url=final_url,
                        status_code=status_code,
                        content_type=content_type,
                        html=response.text if status_code < 500 else None,
                        title=None,
                        meta_description=None,
                        og_title=None,
                        og_description=None,
                        json_ld=None,
                        clean_text="",
                        fetch_method="failed",
                        error=f"HTTP_{status_code}",
                    )

                html_content = response.text
                return self.parse_html(url, final_url, status_code, content_type, html_content)

        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching URL: {url}")
            return FetchedDocument(
                url=url,
                final_url=url,
                status_code=0,
                content_type="",
                html=None,
                title=None,
                meta_description=None,
                og_title=None,
                og_description=None,
                json_ld=None,
                clean_text="",
                fetch_method="failed",
                error="TIMEOUT",
            )
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}", exc_info=True)
            return FetchedDocument(
                url=url,
                final_url=url,
                status_code=0,
                content_type="",
                html=None,
                title=None,
                meta_description=None,
                og_title=None,
                og_description=None,
                json_ld=None,
                clean_text="",
                fetch_method="failed",
                error=str(e),
            )

    def parse_html(
        self,
        url: str,
        final_url: str,
        status_code: int,
        content_type: str,
        html_content: str,
    ) -> FetchedDocument:
        """
        Trích xuất metadata (Title, OG tags, JSON-LD) và làm sạch text từ HTML.
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Trích xuất Title và Meta tags
        page_title = None
        title_tag = soup.find("title")
        if title_tag:
            page_title = title_tag.get_text(strip=True)

        og_title = None
        og_title_tag = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "og:title"})
        if og_title_tag and og_title_tag.get("content"):
            og_title = og_title_tag["content"].strip()

        meta_desc = None
        desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"name": "Description"})
        if desc_tag and desc_tag.get("content"):
            meta_desc = desc_tag["content"].strip()

        og_desc = None
        og_desc_tag = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "og:description"})
        if og_desc_tag and og_desc_tag.get("content"):
            og_desc = og_desc_tag["content"].strip()

        # 2. Trích xuất Schema.org JSON-LD (JobPosting)
        json_ld_data = None
        ld_scripts = soup.find_all("script", type="application/ld+json")
        for script in ld_scripts:
            try:
                if script.string:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        if data.get("@type") == "JobPosting" or "JobPosting" in str(data.get("@type")):
                            json_ld_data = data
                            break
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and (item.get("@type") == "JobPosting" or "JobPosting" in str(item.get("@type"))):
                                json_ld_data = item
                                break
                        if json_ld_data:
                            break
            except Exception:
                continue

        # 3. Làm sạch text: Xóa các thẻ không mang nội dung tuyển dụng
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "noscript", "iframe", "svg", "form"]):
            tag.decompose()

        # Tìm main content container nếu có
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find(class_=re.compile(r"(job-detail|job-description|jd-content|job_description|detail-content)", re.I))
            or soup.body
            or soup
        )

        raw_text = main_content.get_text(separator="\n", strip=True)
        # Chuẩn hóa khoảng trắng và dòng trống
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)

        # Kiểm tra xem trang có đủ nội dung văn bản hay yêu cầu JS rendering
        if len(clean_text) < self.MIN_CONTENT_LENGTH:
            # Fallback 1: Trích xuất từ Next.js App Router RSC streaming (self.__next_f.push)
            rsc_matches = re.findall(r'"jobDescription":"(.*?)(?<!\\)"', html_content)
            if rsc_matches:
                try:
                    desc_str = rsc_matches[0].encode("utf-8").decode("unicode_escape", errors="ignore")
                    extracted_rsc_desc = BeautifulSoup(desc_str, "html.parser").get_text("\n", strip=True)
                    rsc_reqs = re.findall(r'"jobRequirement":"(.*?)(?<!\\)"', html_content)
                    extracted_rsc_req = ""
                    if rsc_reqs:
                        req_str = rsc_reqs[0].encode("utf-8").decode("unicode_escape", errors="ignore")
                        extracted_rsc_req = BeautifulSoup(req_str, "html.parser").get_text("\n", strip=True)
                    clean_text = f"{page_title or og_title or ''}\n\n{extracted_rsc_desc}\n\n{extracted_rsc_req}".strip()
                except Exception:
                    pass

            # Fallback 2: Trích xuất từ OpenGraph / Meta description
            if len(clean_text) < self.MIN_CONTENT_LENGTH and (og_desc or meta_desc):
                desc_candidate = og_desc or meta_desc
                if len(desc_candidate) >= 40:
                    clean_text = f"{page_title or og_title or 'Job Posting'}\n\n{desc_candidate}".strip()

        if len(clean_text) < self.MIN_CONTENT_LENGTH:
            # Kiểm tra xem có phải SPA (React/Vue/Angular root app)
            has_spa_root = bool(soup.find(id=re.compile(r"(app|root|__next)", re.I)))
            error_code = "JS_REQUIRED" if has_spa_root else "EMPTY_CONTENT"
            return FetchedDocument(
                url=url,
                final_url=final_url,
                status_code=status_code,
                content_type=content_type,
                html=html_content,
                title=page_title or og_title,
                meta_description=meta_desc,
                og_title=og_title,
                og_description=og_desc,
                json_ld=json_ld_data,
                clean_text=clean_text,
                fetch_method="failed",
                error=error_code,
            )

        return FetchedDocument(
            url=url,
            final_url=final_url,
            status_code=status_code,
            content_type=content_type,
            html=html_content,
            title=page_title or og_title,
            meta_description=meta_desc,
            og_title=og_title,
            og_description=og_desc,
            json_ld=json_ld_data,
            clean_text=clean_text,
            fetch_method="httpx",
            error=None,
        )

    async def _fetch_vietnamworks_api(self, url: str) -> Optional[FetchedDocument]:
        """
        Trích xuất trực tiếp thông tin tin tuyển dụng VietnamWorks qua REST Search API bằng jobId.
        Hỗ trợ các URL dạng https://www.vietnamworks.com/...-2097932-jv...
        """
        match = re.search(r"[-/](\d+)-jv", url)
        if not match:
            return None
        job_id = match.group(1)
        api_url = "https://ms.vietnamworks.com/job-search/v1.0/search"
        payload = {
            "userId": 0,
            "query": "",
            "filter": [{"field": "jobId", "value": job_id}],
            "ranges": [],
            "order": [],
            "hitsPerPage": 1,
            "page": 0,
        }
        headers = {
            "User-Agent": self.DEFAULT_HEADERS["User-Agent"],
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
                resp = await client.post(api_url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("data", [])
                    if items:
                        item = items[0]
                        title = item.get("jobTitle") or "VietnamWorks Job"
                        company = item.get("companyName") or "VietnamWorks Employer"
                        desc_html = item.get("jobDescription") or ""
                        req_html = item.get("jobRequirement") or ""
                        clean_desc = BeautifulSoup(desc_html, "html.parser").get_text("\n", strip=True)
                        clean_req = BeautifulSoup(req_html, "html.parser").get_text("\n", strip=True)
                        clean_text = f"Vị trí: {title}\nCông ty: {company}\n\nMÔ TẢ CÔNG VIỆC:\n{clean_desc}\n\nYÊU CẦU CÔNG VIỆC:\n{clean_req}"
                        return FetchedDocument(
                            url=url,
                            final_url=url,
                            status_code=200,
                            content_type="application/json",
                            html=f"<div><h1>{title}</h1><h2>{company}</h2>{desc_html}{req_html}</div>",
                            title=title,
                            meta_description=clean_desc[:200],
                            og_title=title,
                            og_description=clean_desc[:200],
                            json_ld=None,
                            clean_text=clean_text,
                            fetch_method="httpx",
                            error=None,
                        )
        except Exception as e:
            logger.warning(f"Failed to fetch VietnamWorks job via search API: {e}")
        return None



url_fetcher = URLFetcher()
