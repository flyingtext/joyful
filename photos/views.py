from __future__ import annotations

from django.db.models import Q
from rest_framework import permissions, viewsets
from rest_framework.pagination import PageNumberPagination

from photos.models import Album, AlbumShare, Photo, PhotoTag, PhotoVisibility, Tag
from photos.serializers import (
    AlbumSerializer,
    AlbumShareSerializer,
    PhotoSerializer,
    PhotoTagSerializer,
    TagSerializer,
)


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class IsOwnerOrSharedReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(obj, "owner", None) == request.user:
            return True
        if isinstance(obj, AlbumShare) and obj.album.owner == request.user:
            return True
        if request.method in permissions.SAFE_METHODS:
            if hasattr(obj, "visibility") and obj.visibility in {
                PhotoVisibility.PUBLIC,
                PhotoVisibility.SHARED,
            }:
                return True
            if isinstance(obj, AlbumShare) and obj.shared_with == request.user:
                return True
        return False


class PhotoViewSet(viewsets.ModelViewSet):
    serializer_class = PhotoSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrSharedReadOnly]
    pagination_class = StandardPagination

    def get_queryset(self):
        user = self.request.user
        queryset = (
            Photo.objects.select_related("owner")
            .prefetch_related("photo_tags__tag")
            .filter(
                Q(owner=user)
                | Q(visibility=PhotoVisibility.PUBLIC)
                | Q(visibility=PhotoVisibility.SHARED)
            )
        )
        owner_filter = self.request.query_params.get("owner")
        tag_filter = self.request.query_params.get("tag")
        if owner_filter:
            queryset = queryset.filter(owner_id=owner_filter)
        if tag_filter:
            queryset = queryset.filter(photo_tags__tag__name__iexact=tag_filter)
        return queryset.distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class AlbumViewSet(viewsets.ModelViewSet):
    serializer_class = AlbumSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrSharedReadOnly]
    pagination_class = StandardPagination

    def get_queryset(self):
        user = self.request.user
        queryset = Album.objects.select_related("owner", "cover_photo").filter(
            Q(owner=user)
            | Q(visibility=PhotoVisibility.PUBLIC)
            | Q(shares__shared_with=user)
        )
        owner_filter = self.request.query_params.get("owner")
        if owner_filter:
            queryset = queryset.filter(owner_id=owner_filter)
        return queryset.distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class AlbumShareViewSet(viewsets.ModelViewSet):
    serializer_class = AlbumShareSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrSharedReadOnly]
    pagination_class = StandardPagination

    def get_queryset(self):
        user = self.request.user
        return AlbumShare.objects.select_related("album", "shared_with", "album__owner").filter(
            Q(album__owner=user) | Q(shared_with=user)
        )


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    queryset = Tag.objects.all()


class PhotoTagViewSet(viewsets.ModelViewSet):
    serializer_class = PhotoTagSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        user = self.request.user
        return PhotoTag.objects.select_related("photo", "tag").filter(photo__owner=user)
