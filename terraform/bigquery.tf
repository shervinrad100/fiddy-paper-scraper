resource "google_bigquery_dataset" "patents" {
  dataset_id = "patents"
  project    = var.project_id
  location   = "US"
  description = "Dataset for bio-relevant patent data"
}

resource "google_bigquery_table" "bio_patents" {
  dataset_id = google_bigquery_dataset.patents.dataset_id
  table_id   = "bio_related_patents"
  project    = var.project_id

  schema = jsonencode([
    { name = "title",         type = "STRING",     mode = "NULLABLE" },
    { name = "abstract",      type = "STRING",     mode = "NULLABLE" },
    { name = "description",   type = "STRING",     mode = "NULLABLE" },
    { name = "inventors",     type = "STRING",     mode = "REPEATED" },
    { name = "filing_date",   type = "DATE",       mode = "NULLABLE" },
    { name = "patent_number", type = "STRING",     mode = "NULLABLE" },
    { name = "ipcr_code",     type = "STRING",     mode = "REPEATED" },
    { name = "cpc_code",      type = "STRING",     mode = "REPEATED" },
    { name = "tags",          type = "STRING",     mode = "REPEATED" },
    { name = "source_file",   type = "STRING",     mode = "NULLABLE" },
  ])
}
