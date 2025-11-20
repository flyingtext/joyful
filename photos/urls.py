from django.urls import include, path
from rest_framework.routers import DefaultRouter

from photos.views import (
    AlbumShareViewSet,
    AlbumViewSet,
    PhotoTagViewSet,
    PhotoViewSet,
    TagViewSet,
)

app_name = "photos"

router = DefaultRouter()
router.register(r"photos", PhotoViewSet, basename="photo")
router.register(r"albums", AlbumViewSet, basename="album")
router.register(r"tags", TagViewSet, basename="tag")
router.register(r"album-shares", AlbumShareViewSet, basename="albumshare")
router.register(r"photo-tags", PhotoTagViewSet, basename="phototag")

urlpatterns = [
    path("", include(router.urls)),
]
