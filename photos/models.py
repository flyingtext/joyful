from django.conf import settings
from django.db import models


class PhotoVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    PRIVATE = "private", "Private"
    SHARED = "shared", "Shared"


class StorageBackend(models.TextChoices):
    LOCAL = "local", "Local"
    S3 = "s3", "S3"


class TagSource(models.TextChoices):
    AI = "ai", "AI"
    MANUAL = "manual", "Manual"


class AlbumPermission(models.TextChoices):
    VIEW = "view", "View"
    COMMENT = "comment", "Comment"


class Photo(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="photos"
    )
    file = models.FileField(
        max_length=512, upload_to="photos/originals/", null=True
    )
    thumbnail = models.ImageField(
        max_length=512, upload_to="photos/thumbnails/", blank=True, null=True
    )
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    taken_at = models.DateTimeField(null=True, blank=True)
    camera_make = models.CharField(max_length=255, blank=True)
    camera_model = models.CharField(max_length=255, blank=True)
    lens_model = models.CharField(max_length=255, blank=True)
    aperture = models.CharField(max_length=50, blank=True)
    shutter_speed = models.CharField(max_length=50, blank=True)
    focal_length = models.CharField(max_length=50, blank=True)
    iso = models.PositiveIntegerField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    visibility = models.CharField(
        max_length=20, choices=PhotoVisibility.choices, default=PhotoVisibility.PRIVATE
    )
    storage_backend = models.CharField(
        max_length=20, choices=StorageBackend.choices, default=StorageBackend.LOCAL
    )
    checksum = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.title or f"Photo {self.pk}"


class Album(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="albums"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cover_photo = models.ForeignKey(
        Photo, null=True, blank=True, on_delete=models.SET_NULL, related_name="cover_for"
    )
    visibility = models.CharField(
        max_length=20, choices=PhotoVisibility.choices, default=PhotoVisibility.PRIVATE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.title


class AlbumShare(models.Model):
    album = models.ForeignKey(
        Album, on_delete=models.CASCADE, related_name="shares"
    )
    shared_with = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="album_shares",
        null=True,
        blank=True,
    )
    share_link_token = models.CharField(max_length=128, unique=True)
    permission = models.CharField(
        max_length=20, choices=AlbumPermission.choices, default=AlbumPermission.VIEW
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"Share for {self.album_id}"


class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.name


class PhotoTag(models.Model):
    photo = models.ForeignKey(
        Photo, on_delete=models.CASCADE, related_name="photo_tags"
    )
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="tagged_photos")
    source = models.CharField(
        max_length=20, choices=TagSource.choices, default=TagSource.MANUAL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("photo", "tag", "source")
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.tag.name} → {self.photo_id}"
