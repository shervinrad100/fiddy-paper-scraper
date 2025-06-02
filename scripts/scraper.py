# from bs4 import BeautifulSoup
from google.cloud import storage, bigquery
import yaml
import openai
import json
from lxml import etree
from io import BytesIO


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

def stream_blob_content(source_blob):
    """
    Iterates over the XML one patent at a time (identified by 'us-patent-application')

    TODO if not bio related store in queue to check with gpt
    TODO instead of .// search for direct address to optimise
    TODO more logging
    """

    with source_blob.open("rb") as f:
        print(f'Opened file {source_blob.name}')
        context = etree.iterparse(f, events=("end", ), tag="us-patent-application", recover=True, huge_tree=True)
        for _, patent in context:        
            yield patent
            print('clearing buffer')
            patent.clear()
            # while patent.getprevious() is not None:
            #     del patent.getparent()[0]
            print('cleared')

def read_patent(patent):
    def _extract_classification(patent):
        for cls in patent.findall(".//classification-ipcr"):
            section = cls.findtext("section")
            class_ = cls.findtext("class")
            subclass = cls.findtext("subclass")
            main_group = cls.findtext("main-group")
            if section and class_ and subclass and main_group:
                code = f"{section}{class_}{subclass}{main_group}"
        
        return {
            "ipcr_code": code,
            "cpc_code": None,
        }

    def _extract_fields(patent):
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

            return {
                "title": title,
                "abstract": abstract_text,
                "description": description_text,
                "inventors": inventors,
                "filing_date": filing_date,
                "patent_num": patent_num,
            }

    output = {**_extract_fields(patent), **_extract_classification(patent)}
    return output

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
    bucket = gcs_client.bucket(BUCKET_NAME)
    bq_client = bigquery.Client()


    files = [blob for blob in bucket.list_blobs() if blob.name.endswith(".xml")]

    for file in files:
        print(f"Processing: {file.name}")

        for patent in stream_blob_content(file):
            row = read_patent(patent)
            print(row["ipcr_code"])
            # row["source_file"] = file.name
            # row["tags"] = None # TODO add with gpt
            print('patent processed')
            # insert_row_to_bq(bq_client, {**row, "source_file":file.name, "tags":None})


if __name__ == "__main__":
    main()
