from __future__ import annotations

import os

from .artifacts import DecisionArtifacts


class GCSObjectStore:
    """Write immutable private objects to a hardened GCS bucket."""

    def __init__(self, bucket_name: str, prefix: str = "jurisprudence") -> None:
        try:
            from google.cloud import storage
        except ImportError as exc:
            raise RuntimeError("Install the GCS dependency: pip install '.[gcs]'") from exc
        access_token = os.environ.get("GOOGLE_OAUTH_ACCESS_TOKEN")
        if access_token:
            from google.oauth2.credentials import Credentials

            credentials = Credentials(token=access_token)
            client = storage.Client(
                project=os.environ.get("GOOGLE_CLOUD_PROJECT"), credentials=credentials
            )
        else:
            client = storage.Client()
        self.bucket = client.bucket(bucket_name)
        self.bucket.reload()
        iam = self.bucket.iam_configuration
        if iam.public_access_prevention != "enforced":
            raise RuntimeError("GCS bucket must enforce public access prevention")
        if not iam.uniform_bucket_level_access_enabled:
            raise RuntimeError("GCS bucket must enable uniform bucket-level access")
        self.prefix = prefix.strip("/")

    def upload_bytes(
        self,
        name: str,
        data: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> bool:
        """Create an object once; return False when the immutable object exists."""
        from google.api_core.exceptions import PreconditionFailed

        object_name = f"{self.prefix}/{name.lstrip('/')}" if self.prefix else name.lstrip("/")
        blob = self.bucket.blob(object_name)
        blob.metadata = metadata or {}
        try:
            blob.upload_from_string(
                data,
                content_type=content_type,
                if_generation_match=0,
                checksum="auto",
            )
        except PreconditionFailed:
            return False
        return True


class GCSArtifactStore:
    def __init__(self, bucket_name: str, prefix: str = "jurisprudence") -> None:
        self.objects = GCSObjectStore(bucket_name, prefix)

    def upload(self, bundle: DecisionArtifacts) -> tuple[int, int]:
        uploaded = 0
        existing = 0
        for item in bundle.objects:
            if self.objects.upload_bytes(
                item.name,
                item.data,
                item.content_type,
                {
                    "sha256": item.sha256,
                    "requires-human-review": str(bundle.requires_human_review).lower(),
                },
            ):
                uploaded += 1
            else:
                existing += 1
        return uploaded, existing
