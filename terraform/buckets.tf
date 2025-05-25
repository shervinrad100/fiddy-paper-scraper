resource "google_storage_bucket" "raw_patents" {
    name = "${var.project_id}-patent-raw"
    location = var.region
    force_destroy = true
}

