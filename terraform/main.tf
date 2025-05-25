resource "google_project_service" "required_apis" {
  for_each = toset([
    "compute.googleapis.com",
    "storage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "composer.googleapis.com",
    "bigquery.googleapis.com",
  ])

  service = each.key
  project = var.project_id

  disable_on_destroy = false
}

resource "google_compute_instance" "scraper_vm" {
    name         = "patent-scraper"
    machine_type = "e2-medium" # because we are doing NLP
    zone         = "${var.region}-b"

    network_interface {
        network = "default"
        access_config {} # in case I need to ssh
    }

    # TODO automate setup
    # metadata_startup_script = file("startup-script.sh")
}
