import hashlib

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.core.files.uploadedfile import SimpleUploadedFile
from photos.models import Photo, PhotoTag, PhotoVisibility, Tag, TagSource
from users.models import User


class PhotoAPITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            email="owner@example.com", password="testpass", name="Owner"
        )
        self.other_user = User.objects.create_user(
            email="viewer@example.com", password="testpass", name="Viewer"
        )

    def test_upload_creates_checksum_and_tags(self):
        self.client.force_authenticate(self.owner)
        file_bytes = b"example image bytes"
        checksum = hashlib.sha256(file_bytes).hexdigest()
        upload = SimpleUploadedFile("sample.jpg", file_bytes, content_type="image/jpeg")
        response = self.client.post(
            reverse("photos:photo-list"),
            {
                "uploaded_file": upload,
                "title": "Sample",
                "tags": ["travel", "summer"],
                "visibility": PhotoVisibility.PRIVATE,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        photo = Photo.objects.get(pk=response.data["id"])
        self.assertEqual(photo.owner, self.owner)
        self.assertEqual(photo.checksum, checksum)
        self.assertEqual(
            set(photo.photo_tags.values_list("tag__name", flat=True)),
            {"travel", "summer"},
        )

    def test_filtering_by_visibility_owner_and_tag(self):
        public_photo = Photo.objects.create(
            owner=self.owner,
            file="photos/originals/public.jpg",
            checksum="checksum-public",
            visibility=PhotoVisibility.PUBLIC,
            title="Public Photo",
        )
        private_photo = Photo.objects.create(
            owner=self.owner,
            file="photos/originals/private.jpg",
            checksum="checksum-private",
            visibility=PhotoVisibility.PRIVATE,
            title="Private Photo",
        )
        shared_photo = Photo.objects.create(
            owner=self.other_user,
            file="photos/originals/shared.jpg",
            checksum="checksum-shared",
            visibility=PhotoVisibility.SHARED,
            title="Shared Photo",
        )
        travel_tag = Tag.objects.create(name="travel")
        PhotoTag.objects.create(
            photo=public_photo, tag=travel_tag, source=TagSource.MANUAL
        )

        list_url = reverse("photos:photo-list")

        # Anonymous users only see public photos
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], public_photo.id)

        # Tag filter returns only matching tagged photos
        response = self.client.get(list_url, {"tag": "travel"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], public_photo.id)

        # Authenticated user can see their private photo and shared ones
        self.client.force_authenticate(self.owner)
        response = self.client.get(list_url, {"visibility": PhotoVisibility.PRIVATE})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], private_photo.id)

        response = self.client.get(list_url, {"visibility": PhotoVisibility.SHARED})
        returned_ids = {item["id"] for item in response.data["results"]}
        self.assertIn(shared_photo.id, returned_ids)
        self.assertNotIn(private_photo.id, returned_ids)
