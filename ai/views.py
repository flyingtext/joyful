from __future__ import annotations

from django.db.models import Q
from rest_framework import permissions, viewsets
from rest_framework.pagination import PageNumberPagination

from ai.models import AICaptionJob
from ai.serializers import AICaptionJobSerializer
from photos.models import PhotoVisibility


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AICaptionJobViewSet(viewsets.ModelViewSet):
    serializer_class = AICaptionJobSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        user = self.request.user
        queryset = AICaptionJob.objects.select_related("photo", "photo__owner").filter(
            Q(photo__owner=user) | Q(photo__visibility=PhotoVisibility.PUBLIC)
        )
        photo_filter = self.request.query_params.get("photo")
        if photo_filter:
            queryset = queryset.filter(photo_id=photo_filter)
        return queryset
