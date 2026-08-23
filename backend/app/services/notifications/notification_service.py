import abc
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationPayload(BaseModel):
    title: str = Field(..., description="Tiêu đề thông báo")
    message: str = Field(..., description="Nội dung tóm tắt thông báo")
    notification_type: str = Field("INFO", description="INFO, HIGH_MATCH, DAILY_DIGEST, STATUS_UPDATE")
    fields: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    action_url: Optional[str] = Field(None, description="Link điều hướng về Web Application")


class NotificationProvider(abc.ABC):
    """
    Interface trừu tượng cho các Notification Provider (Discord, Email, Webhook, v.v.).
    Đảm bảo Domain Core không bị phụ thuộc cứng vào Discord.
    """
    @abc.abstractmethod
    async def send(self, payload: NotificationPayload) -> bool:
        pass


class ConsoleNotificationProvider(NotificationProvider):
    """
    Fallback provider ghi thông báo ra standard logger / console.
    """
    async def send(self, payload: NotificationPayload) -> bool:
        logger.info(
            f"[Notification - {payload.notification_type}] {payload.title}: {payload.message}"
            + (f" | Web Link: {payload.action_url}" if payload.action_url else "")
        )
        return True


class DiscordNotificationProvider(NotificationProvider):
    """
    Provider gửi thông báo qua Discord Webhook hoặc Discord Bot API.
    """
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or settings.DISCORD_WEBHOOK_URL

    async def send(self, payload: NotificationPayload) -> bool:
        if not self.webhook_url:
            logger.debug("Discord webhook URL is not configured. Skipping Discord delivery.")
            return False

        color_map = {
            "HIGH_MATCH": 0x2563EB,    # Blue
            "DAILY_DIGEST": 0x10B981,  # Green
            "STATUS_UPDATE": 0xF59E0B, # Amber
            "INFO": 0x6B7280           # Gray
        }
        embed_color = color_map.get(payload.notification_type, 0x2563EB)

        embed_fields = []
        if payload.fields:
            for f in payload.fields:
                embed_fields.append({
                    "name": str(f.get("name", "")),
                    "value": str(f.get("value", "")),
                    "inline": bool(f.get("inline", True))
                })

        # Bổ sung nút liên kết về Web App
        description = payload.message
        if payload.action_url:
            description += f"\n\n🔗 **[Mở trên Web Application]({payload.action_url})**"

        embed = {
            "title": f"🚀 {payload.title}",
            "description": description,
            "color": embed_color,
            "fields": embed_fields,
            "footer": {
                "text": "Job Hunter Platform • Web Application-First"
            }
        }

        discord_payload = {
            "embeds": [embed]
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url, json=discord_payload)
                if response.status_code in (200, 204):
                    logger.info(f"Successfully dispatched Discord notification: {payload.title}")
                    return True
                else:
                    logger.warning(
                        f"Discord webhook failed with status {response.status_code}: {response.text}"
                    )
                    return False
        except Exception as e:
            logger.error(f"Error dispatching Discord notification: {e}")
            return False


class NotificationService:
    """
    Quản lý và điều phối gửi thông báo đa kênh (Web-first notification hub).
    """
    def __init__(self):
        self.providers: List[NotificationProvider] = [
            ConsoleNotificationProvider()
        ]
        if settings.DISCORD_WEBHOOK_URL:
            self.providers.append(DiscordNotificationProvider(settings.DISCORD_WEBHOOK_URL))

    def register_provider(self, provider: NotificationProvider) -> None:
        self.providers.append(provider)

    async def notify(self, payload: NotificationPayload) -> Dict[str, bool]:
        results = {}
        for provider in self.providers:
            provider_name = provider.__class__.__name__
            try:
                success = await provider.send(payload)
                results[provider_name] = success
            except Exception as e:
                logger.error(f"Provider {provider_name} failed: {e}")
                results[provider_name] = False
        return results

    async def notify_high_match(self, job_title: str, company: str, score: float, job_id: str) -> None:
        web_url = f"http://localhost:3000/jobs/{job_id}"
        payload = NotificationPayload(
            title=f"New High Match Job ({score:.0f}/100)",
            message=f"Phát hiện công việc phù hợp cao: **{job_title}** tại **{company}**.",
            notification_type="HIGH_MATCH",
            fields=[
                {"name": "Điểm phù hợp", "value": f"{score:.1f}%", "inline": True},
                {"name": "Công ty", "value": company, "inline": True},
            ],
            action_url=web_url,
        )
        await self.notify(payload)

    async def notify_daily_digest(self, total_jobs: int, top_matches_count: int, top_job_title: Optional[str] = None) -> None:
        payload = NotificationPayload(
            title="Daily Job Intelligence Digest",
            message=f"Tổng kết quét tự động hôm nay: **{total_jobs}** tin mới, **{top_matches_count}** vị trí tiềm năng cao.",
            notification_type="DAILY_DIGEST",
            fields=[
                {"name": "Tin đã quét", "value": str(total_jobs), "inline": True},
                {"name": "Vị trí đề xuất cao", "value": str(top_matches_count), "inline": True},
            ],
            action_url="http://localhost:3000/dashboard",
        )
        await self.notify(payload)


notification_service = NotificationService()
