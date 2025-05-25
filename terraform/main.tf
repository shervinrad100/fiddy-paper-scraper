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
    allow_stopping_for_update = true

    network_interface {
        network = "default"
        access_config {} # in case I need to ssh
    }

    service_account {
      email  = var.vm_sa
      scopes = ["cloud-platform"]
    }

    boot_disk {
      initialize_params {
        image = "debian-cloud/debian-11"
      }
    }

    metadata_startup_script = file("startup-script.sh")
    
    # to manually ssh into the VM
    # gcloud auth application-default set-quota-project fiddy-paper-scraper
    # gcloud compute ssh scraper-vm --zone=us-central1-b
}