# TODO need to provision role for terraform to run from VM instead of my local
# terraform {
#   backend "gcs" {
#     bucket  = "tfstate-paper-scraper"
#     prefix  = "envs/dev/paper-scraper"
#   }
# }

provider "google" {
    project = var.project_id
    region = var.region
    # impersonate_service_account = var.vm_sa
}