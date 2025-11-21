from __future__ import annotations

import hashlib
import os
import secrets
from typing import Iterable

from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework import serializers

from photos.models import (
    Album,
    AlbumPermission,
    AlbumShare,
    Photo,
    PhotoTag,
    PhotoVisibility,
    StorageBackend,
    Tag,
    TagSource,
)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


class PhotoSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.id")
    uploaded_file = serializers.FileField(write_only=True, required=False)
    tags = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False, allow_empty=True
    )
    tag_names = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Photo
        fields = [
            "id",
            "owner",
            "file",
            "thumbnail",
            "title",
            "description",
            "width",
            "height",
            "taken_at",
            "camera_make",
            "camera_model",
            "lens_model",
            "aperture",
            "shutter_speed",
            "focal_length",
            "iso",
            "latitude",
            "longitude",
            "location",
            "visibility",
            "storage_backend",
            "checksum",
            "created_at",
            "uploaded_file",
            "tags",
            "tag_names",
        ]
        read_only_fields = [
            "id",
            "checksum",
            "created_at",
            "thumbnail",
            "file",
        ]

    def validate_visibility(self, value: str) -> str:
        if value not in PhotoVisibility.values:
            raise serializers.ValidationError("Invalid visibility option")
        return value

    def validate_storage_backend(self, value: str) -> str:
        if value not in StorageBackend.values:
            raise serializers.ValidationError("Invalid storage backend")
        return value

    def validate(self, attrs):
        uploaded_file = attrs.get("uploaded_file")
        checksum = attrs.get("checksum")
        if not uploaded_file and not checksum and self.instance is None:
            raise serializers.ValidationError(
                "Either an uploaded file or checksum must be provided"
            )
        return attrs

    def _prepare_file(self, uploaded_file) -> tuple[str, str]:
        content = uploaded_file.read()
        checksum = hashlib.sha256(content).hexdigest()
        uploaded_file.seek(0)
        storage_path = default_storage.save(
            os.path.join("photos", "originals", uploaded_file.name), uploaded_file
        )
        return storage_path, checksum

    def _sync_tags(self, photo: Photo, tag_names: Iterable[str]) -> None:
        normalized = [name.strip() for name in tag_names if name.strip()]
        tags = []
        for name in normalized:
            tag, _ = Tag.objects.get_or_create(name=name)
            tags.append(tag)
        PhotoTag.objects.filter(photo=photo, source=TagSource.MANUAL).exclude(
            tag__in=tags
        ).delete()
        for tag in tags:
            PhotoTag.objects.get_or_create(
                photo=photo, tag=tag, source=TagSource.MANUAL
            )

    def create(self, validated_data):
        uploaded_file = validated_data.pop("uploaded_file", None)
        tag_names = validated_data.pop("tags", [])
        owner = self.context["request"].user
        if uploaded_file:
            storage_path, checksum = self._prepare_file(uploaded_file)
            validated_data["file"] = storage_path
            validated_data["checksum"] = checksum
        with transaction.atomic():
            photo = Photo.objects.create(owner=owner, **validated_data)
            if tag_names:
                self._sync_tags(photo, tag_names)
        return photo

    def update(self, instance: Photo, validated_data):
        uploaded_file = validated_data.pop("uploaded_file", None)
        tag_names = validated_data.pop("tags", None)
        if uploaded_file:
            storage_path, checksum = self._prepare_file(uploaded_file)
            validated_data["file"] = storage_path
            validated_data["checksum"] = checksum
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tag_names is not None:
            self._sync_tags(instance, tag_names)
        return instance

    def get_tag_names(self, obj: Photo) -> list[str]:
        return [pt.tag.name for pt in obj.photo_tags.select_related("tag")]


class AlbumSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.id")

    class Meta:
        model = Album
        fields = [
            "id",
            "owner",
            "title",
            "description",
            "cover_photo",
            "visibility",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_visibility(self, value: str) -> str:
        if value not in PhotoVisibility.values:
            raise serializers.ValidationError("Invalid visibility option")
        return value

    def validate_cover_photo(self, value: Photo | None) -> Photo | None:
        if value and value.owner != self.context["request"].user:
            raise serializers.ValidationError("Cover photo must belong to you")
        return value

    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)


class AlbumShareSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="album.owner.id")

    class Meta:
        model = AlbumShare
        fields = [
            "id",
            "album",
            "shared_with",
            "share_link_token",
            "permission",
            "expires_at",
            "created_at",
            "owner",
        ]
        read_only_fields = ["id", "created_at", "owner"]
        extra_kwargs = {"share_link_token": {"required": False}}

    def validate_share_link_token(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("Share link token cannot be empty")
        if len(value) < 8:
            raise serializers.ValidationError("Share link token must be at least 8 characters")
        return value

    def validate_permission(self, value: str) -> str:
        if value not in AlbumPermission.values:
            raise serializers.ValidationError("Invalid permission option")
        return value

    def validate_album(self, value: Album) -> Album:
        if value.owner != self.context["request"].user:
            raise serializers.ValidationError("You can only share your own albums")
        return value

    def create(self, validated_data):
        if not validated_data.get("share_link_token"):
            validated_data["share_link_token"] = secrets.token_urlsafe(16)
        return super().create(validated_data)


class PhotoTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotoTag
        fields = ["id", "photo", "tag", "source", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_source(self, value: str) -> str:
        if value not in TagSource.values:
            raise serializers.ValidationError("Invalid tag source")
        return value

    def validate_photo(self, value: Photo) -> Photo:
        request = self.context.get("request")
        if request and value.owner != request.user:
            raise serializers.ValidationError("You can only tag your own photos")
        return value
