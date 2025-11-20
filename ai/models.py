from django.db import models

from photos.models import Photo


class CaptionJobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class AICaptionJob(models.Model):
    photo = models.ForeignKey(
        Photo, on_delete=models.CASCADE, related_name="caption_jobs"
    )
    status = models.CharField(
        max_length=20, choices=CaptionJobStatus.choices, default=CaptionJobStatus.PENDING
    )
    model = models.CharField(max_length=100)
    caption_ko = models.TextField(blank=True)
    raw_response = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"Caption job {self.pk} for photo {self.photo_id}"
