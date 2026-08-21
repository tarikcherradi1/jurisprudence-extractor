from __future__ import annotations

from .artifacts import DecisionArtifacts


class GCSArtifactStore:
    def __init__(self, bucket_name: str, prefix: str = "jurisprudence") -> None:
        try:
            from google.cloud import storage
        except ImportError as exc:
            raise RuntimeError("Install the GCS dependency: pip install '.[gcs]'") from exc
        self.bucket = storage.Client().bucket(bucket_name)
        self.bucket.reload()
        iam = self.bucket.iam_configuration
        if iam.public_access_prevention != "enforced":
            raise RuntimeError("GCS bucket must enforce public access prevention")
        if not iam.uniform_bucket_level_access_enabled:
            raise RuntimeError("GCS bucket must enable uniform bucket-level access")
        self.prefix = prefix.strip("/")

    def upload(self, bundle: DecisionArtifacts) -> tuple[int, int]:
        from google.api_core.exceptions import PreconditionFailed

        uploaded = 0
        existing = 0
        for item in bundle.objects:
            name = f"{self.prefix}/{item.name}" if self.prefix else item.name
            blob = self.bucket.blob(name)
            blob.metadata = {
                "sha256": item.sha256,
                "requires-human-review": str(bundle.requires_human_review).lower(),
            }
            try:
                blob.upload_from_string(
                    item.data,
                    content_type=item.content_type,
                    if_generation_match=0,
                    checksum="auto",
                )
                uploaded += 1
            except PreconditionFailed:
                existing += 1
        return uploaded, existing
