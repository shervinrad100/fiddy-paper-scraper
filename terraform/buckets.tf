resource "google_storage_bucket" "raw_patents" {
    name = "${var.project_id}-patent-raw"
    location = var.region
    force_destroy = true
}

resource "google_storage_bucket_iam_member" "sa_storage_admin" {
  bucket = "fiddy-paper-scraper-patent-raw"
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.vm_sa}"
}