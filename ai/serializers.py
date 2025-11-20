from __future__ import annotations

from rest_framework import serializers

from ai.models import AICaptionJob, CaptionJobStatus
from photos.models import Photo, PhotoVisibility


class AICaptionJobSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source="photo.owner.id")

    class Meta:
        model = AICaptionJob
        fields = [
            "id",
            "photo",
            "status",
            "model",
            "caption_ko",
            "raw_response",
            "error_message",
            "started_at",
            "finished_at",
            "created_at",
            "owner",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "owner",
            "started_at",
            "finished_at",
            "raw_response",
            "error_message",
        ]

    def validate_status(self, value: str) -> str:
        if value not in CaptionJobStatus.values:
            raise serializers.ValidationError("Invalid status")
        return value

    def validate_photo(self, value: Photo) -> Photo:
        request = self.context.get("request")
        if request and value.owner != request.user:
            raise serializers.ValidationError("Photo must belong to the requesting user")
        if value.visibility == PhotoVisibility.PRIVATE and value.owner != request.user:
            raise serializers.ValidationError("You cannot caption a private photo you do not own")
        return value

    def create(self, validated_data):
        validated_data.setdefault("status", CaptionJobStatus.PENDING)
        return super().create(validated_data)
