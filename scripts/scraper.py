# from bs4 import BeautifulSoup
from google.cloud import storage, bigquery
import yaml
import openai
import json
from lxml import etree


BUCKET_NAME = "fiddy-paper-scraper-patent-raw"
PROJECT_ID = "fiddy-paper-scraper"
BQ_DATASET = "patents"
BQ_TABLE = "bio_related_patents"
IPCR_CODES=set([    
    "A01H", "A01K",         # Agriculture/genetics
    "C07K", "C07H",         # Peptides/DNA
    "C12N", "C12P", "C12Q", # Core biotech
    "A61K", "A61P",         # Pharma
])
GPT_PROMPT = """
You are a patent analyst. Given the title, abstract and claims of a US patent application, determine if it is related to biotechnology.
Respond only with true or false.
"""

with open("secrets.yaml") as f:
    secrets = yaml.safe_load(f)
    openai.api_key = secrets["openai"]["api_key"]

def download_latest_patents():
    """get latest patents from USPTO API (Patent Application Full-Text Data (No Images))
    Will be scheduled on airflow so we can configure the date there
    needs to unzip the files 
    """
    return

def fetch_gcs_files(gcs_client, filter=None):
    """read patent file from GCS
    TODO filter for date downloaded again should be configured in airflow
    """
    bucket = gcs_client.bucket(BUCKET_NAME)
    return [blob.name for blob in bucket.list_blobs() if blob.name.endswith(".xml")]

def stream_blob_content(gcs_client, blob_name):
    """
    Iterates over the XML one patent at a time (identified by 'us-patent-application')
    checks to see if the patent is bio related 
    if it is, it will pull out the title, description, etc and put it in bigquery

    TODO if not bio related store in queue to check with gpt
    TODO instead of .// search for direct address to optimise
    TODO more logging
    """
    bucket = gcs_client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)

    with blob.open("rb") as f:
        print(f'opened file {blob_name}')
        context = etree.iterparse(f, events=("end", ), tag="us-patent-application", recover=True)

        for _, patent in context:
            # is it bio related?
            # ask chatgpt or choose from pre-fitlered codes (more efficient)
            for cls in patent.findall(".//classification-ipcr"):
                section = cls.findtext("section")
                class_ = cls.findtext("class")
                subclass = cls.findtext("subclass")
                main_group = cls.findtext("main-group")
                if section and class_ and subclass and main_group:
                    code = f"{section}{class_}{subclass}{main_group}"
            print(code)
            if code not in IPCR_CODES:
                patent.clear()
                continue

            title = patent.findtext(".//invention-title", default="").strip()
            abstract = patent.find(".//abstract")
            abstract_text = etree.tostring(abstract, method="text", encoding="unicode").strip() if abstract is not None else ""

            description = patent.find(".//description")
            description_text = etree.tostring(description, method="text", encoding="unicode").strip()[:5000] if description is not None else ""

            inventors = [] # in case there are multiple
            for inventor in patent.findall(".//inventor/addressbook"):
                first = inventor.findtext("first-name", "").strip()
                last = inventor.findtext("last-name", "").strip()
                inventors.append((first, last))

            filing_date = patent.findtext(".//application-reference/document-id/date", default="").strip()
            patent_num = patent.findtext(".//publication-reference/document-id/doc-number", default="").strip()


            output = {
                "title": title,
                "abstract": abstract_text,
                "description": description_text,
                "inventors": inventors,
                "filing_date": filing_date,
                "patent_num": patent_num,
                "ipcr_code": code,
                "cpc_code": None,
            }
            print(output)
            yield output
            patent.clear()
            while patent.getprevious() is not None:
                del patent.getparent()[0]

def query_openai(xml_text):
    """
    TODO if xml is too large it will error
    TODO optimise by reducing num tokens
    TODO use o3 and deep-research gpt
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4", 
            messages=[
                {"role": "system", "content": GPT_PROMPT.strip()},
                {"role": "user", "content": xml_text[:12000]}
            ],
            temperature=0.2,
            max_tokens=500
        )
        content = response["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        print(f"OpenAI error: {e}")
        return None


def insert_row_to_bq(bq_client, row):
    table_ref = bq_client.dataset(BQ_DATASET).table(BQ_TABLE)
    errors = bq_client.insert_rows_json(table_ref, row)
    if errors:
        print(f"BigQuery insert error: {errors}")
        return errors
    # TODO handle errors better and alert in Airflow job
    else:
        print(f"Inserted row: {row['patent_number']}")
        return True


def main():
    gcs_client = storage.Client()
    bq_client = bigquery.Client()

    files = fetch_gcs_files(gcs_client)

    for file_name in files:
        print(f"Processing: {file_name}")

        for patent in stream_blob_content(gcs_client, file_name):
            print(patent)
            patent["source_file"] = file_name
            patent["tags"] = None # TODO add with gpt
            insert_row_to_bq(patent)


if __name__ == "__main__":
    main()
