from __future__ import annotations

import hashlib
import os

from django import forms
from django.core.files.storage import default_storage

from photos.models import Album, AlbumPermission, AlbumShare, Photo, PhotoVisibility, StorageBackend, Tag


class PhotoForm(forms.ModelForm):
    uploaded_file = forms.FileField(required=False)

    class Meta:
        model = Photo
        fields = [
            "file_path",
            "thumbnail_path",
            "title",
            "description",
            "width",
            "height",
            "taken_at",
            "location",
            "visibility",
            "storage_backend",
            "checksum",
            "uploaded_file",
        ]

    def clean_visibility(self):
        value = self.cleaned_data.get("visibility")
        if value not in PhotoVisibility.values:
            raise forms.ValidationError("Invalid visibility value")
        return value

    def clean_storage_backend(self):
        value = self.cleaned_data.get("storage_backend")
        if value not in StorageBackend.values:
            raise forms.ValidationError("Invalid storage backend")
        return value

    def save(self, commit: bool = True):
        uploaded_file = self.cleaned_data.pop("uploaded_file", None)
        if uploaded_file:
            content = uploaded_file.read()
            checksum = hashlib.sha256(content).hexdigest()
            uploaded_file.seek(0)
            path = default_storage.save(os.path.join("photos", uploaded_file.name), uploaded_file)
            self.instance.file_path = path
            self.instance.checksum = checksum
        return super().save(commit=commit)


class AlbumForm(forms.ModelForm):
    class Meta:
        model = Album
        fields = ["title", "description", "cover_photo", "visibility"]

    def clean_visibility(self):
        value = self.cleaned_data.get("visibility")
        if value not in PhotoVisibility.values:
            raise forms.ValidationError("Invalid visibility value")
        return value


class AlbumShareForm(forms.ModelForm):
    class Meta:
        model = AlbumShare
        fields = ["album", "shared_with", "share_link_token", "permission", "expires_at"]

    def clean_share_link_token(self):
        value = self.cleaned_data.get("share_link_token")
        if not value:
            raise forms.ValidationError("Share link token is required")
        if len(value) < 8:
            raise forms.ValidationError("Share link token must be at least 8 characters long")
        return value

    def clean_permission(self):
        value = self.cleaned_data.get("permission")
        if value not in AlbumPermission.values:
            raise forms.ValidationError("Invalid album permission")
        return value


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name"]
