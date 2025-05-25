variable "project_id" {
    default = "fiddy-paper-scraper" # created this with the UI for ease
}

variable "region" {
    default = "us-central1" # because it's cheapest
}

variable "vm_sa" {
    default = "14711625322-compute@developer.gserviceaccount.com"
}