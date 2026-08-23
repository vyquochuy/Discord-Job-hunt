import asyncio
import sys
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup

async def main():
    url = "https://www.topcv.vn/tim-viec-lam-it-phan-mem-c10026?sort=new"
    async with AsyncSession(impersonate="chrome124") as s:
        r = await s.get(url, timeout=15)
        print("Status:", r.status_code)
        soup = BeautifulSoup(r.text, "html.parser")
        job_items = soup.select(".job-item-2, .job-item-search-result, .job-item, .job-ta, [data-job-id]")
        print("Total job items:", len(job_items))
        
        # Let's inspect a few items with data-job-id
        items_with_id = soup.find_all(attrs={"data-job-id": True})
        print("Items with data-job-id:", len(items_with_id))
        for i, it in enumerate(items_with_id[:5]):
            title_a = it.select_one("a[target='_blank'], a[href*='viec-lam'], .title, h3")
            print(f"  Item {i}: tag={it.name}, class={it.get('class')}, title_a={title_a.get_text(strip=True) if title_a else 'None'}, href={title_a.get('href') if title_a and title_a.has_attr('href') else 'None'}")


if __name__ == "__main__":
    asyncio.run(main())
