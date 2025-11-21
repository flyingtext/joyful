from __future__ import annotations

from django.db.models import Q
from rest_framework import filters, permissions, viewsets
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


class PhotoAccessPermission(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj) -> bool:
        if getattr(obj, "owner", None) == getattr(request, "user", None):
            return True
        if request.method in permissions.SAFE_METHODS:
            if getattr(obj, "visibility", None) == PhotoVisibility.PUBLIC:
                return True
            if (
                getattr(obj, "visibility", None) == PhotoVisibility.SHARED
                and request.user
                and request.user.is_authenticated
            ):
                return True
        return False


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


class PhotoFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        owner_filter = request.query_params.get("owner")
        visibility_filter = request.query_params.get("visibility")
        tag_filter = request.query_params.get("tag")

        if owner_filter:
            queryset = queryset.filter(owner_id=owner_filter)
        if visibility_filter:
            queryset = queryset.filter(visibility=visibility_filter)
        if tag_filter:
            queryset = queryset.filter(photo_tags__tag__name__iexact=tag_filter)
        return queryset


class PhotoViewSet(viewsets.ModelViewSet):
    serializer_class = PhotoSerializer
    permission_classes = [PhotoAccessPermission]
    pagination_class = StandardPagination
    filter_backends = [PhotoFilterBackend]

    def get_queryset(self):
        user = self.request.user
        visibility_filter = Q(visibility=PhotoVisibility.PUBLIC)
        shared_filter = Q(visibility=PhotoVisibility.SHARED)

        queryset = Photo.objects.select_related("owner").prefetch_related(
            "photo_tags__tag"
        )

        if user and user.is_authenticated:
            queryset = queryset.filter(Q(owner=user) | visibility_filter | shared_filter)
        else:
            queryset = queryset.filter(visibility_filter)

        return queryset.distinct()


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
