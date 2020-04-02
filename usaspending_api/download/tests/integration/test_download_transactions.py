import json
import pytest
import random

from django.conf import settings
from model_mommy import mommy
from rest_framework import status
from unittest.mock import Mock

from usaspending_api.awards.models import TransactionNormalized, TransactionFABS, TransactionFPDS
from usaspending_api.awards.v2.lookups.lookups import award_type_mapping
from usaspending_api.common.experimental_api_flags import EXPERIMENTAL_API_HEADER, ELASTICSEARCH_HEADER_VALUE
from usaspending_api.download.filestreaming import download_generation
from usaspending_api.common.helpers.generic_helper import generate_test_db_connection_string
from usaspending_api.download.lookups import JOB_STATUS
from usaspending_api.etl.award_helpers import update_awards


@pytest.fixture
def download_test_data(db):
    # Populate job status lookup table
    for js in JOB_STATUS:
        mommy.make("download.JobStatus", job_status_id=js.id, name=js.name, description=js.desc)

    # Create Awarding Top Agency
    ata1 = mommy.make(
        "references.ToptierAgency",
        name="Bureau of Things",
        toptier_code="100",
        website="http://test.com",
        mission="test",
        icon_filename="test",
    )
    ata2 = mommy.make(
        "references.ToptierAgency",
        name="Bureau of Stuff",
        toptier_code="101",
        website="http://test.com",
        mission="test",
        icon_filename="test",
    )

    # Create Awarding subs
    mommy.make("references.SubtierAgency", name="Bureau of Things")

    # Create Awarding Agencies
    aa1 = mommy.make("references.Agency", id=1, toptier_agency=ata1, toptier_flag=False)
    aa2 = mommy.make("references.Agency", id=2, toptier_agency=ata2, toptier_flag=False)

    # Create Funding Top Agency
    ata3 = mommy.make(
        "references.ToptierAgency",
        name="Bureau of Money",
        toptier_code="102",
        website="http://test.com",
        mission="test",
        icon_filename="test",
    )

    # Create Funding SUB
    mommy.make("references.SubtierAgency", name="Bureau of Things")

    # Create Funding Agency
    mommy.make("references.Agency", id=3, toptier_agency=ata3, toptier_flag=False)

    # Create Awards
    award1 = mommy.make("awards.Award", id=123, category="idv")
    award2 = mommy.make("awards.Award", id=456, category="contracts")
    award3 = mommy.make("awards.Award", id=789, category="assistance")

    # Create Transactions
    trann1 = mommy.make(
        TransactionNormalized,
        award=award1,
        action_date="2018-01-01",
        type=random.choice(list(award_type_mapping)),
        modification_number=1,
        awarding_agency=aa1,
    )
    trann2 = mommy.make(
        TransactionNormalized,
        award=award2,
        action_date="2018-01-01",
        type=random.choice(list(award_type_mapping)),
        modification_number=1,
        awarding_agency=aa2,
    )
    trann3 = mommy.make(
        TransactionNormalized,
        award=award3,
        action_date="2018-01-01",
        type=random.choice(list(award_type_mapping)),
        modification_number=1,
        awarding_agency=aa2,
    )

    # Create TransactionContract
    mommy.make(TransactionFPDS, transaction=trann1, piid="tc1piid")
    mommy.make(TransactionFPDS, transaction=trann2, piid="tc2piid")

    # Create TransactionAssistance
    mommy.make(TransactionFABS, transaction=trann3, fain="ta1fain")

    # Set latest_award for each award
    update_awards()


def test_download_transactions_without_columns(client, download_test_data):
    download_generation.retrieve_db_string = Mock(return_value=generate_test_db_connection_string())
    resp = client.post(
        "/api/v2/download/transactions/",
        content_type="application/json",
        data=json.dumps({"filters": {"award_type_codes": []}, "columns": []}),
    )

    assert resp.status_code == status.HTTP_200_OK
    assert ".zip" in resp.json()["file_url"]


def test_download_transactions_with_columns(client, download_test_data):
    download_generation.retrieve_db_string = Mock(return_value=generate_test_db_connection_string())
    resp = client.post(
        "/api/v2/download/transactions/",
        content_type="application/json",
        data=json.dumps(
            {
                "filters": {"award_type_codes": []},
                "columns": [
                    "assistance_transaction_unique_key",
                    "award_id_fain",
                    "modification_number",
                    "sai_number",
                    "contract_transaction_unique_key",
                ],
            }
        ),
    )

    assert resp.status_code == status.HTTP_200_OK
    assert ".zip" in resp.json()["file_url"]


@pytest.mark.django_db
def test_download_transactions_bad_limit(client):
    download_generation.retrieve_db_string = Mock(return_value=generate_test_db_connection_string())
    resp = client.post(
        "/api/v2/download/transactions/",
        content_type="application/json",
        data=json.dumps({"limit": "wombats", "filters": {"award_type_codes": []}, "columns": []}),
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_download_transactions_excessive_limit(client, download_test_data):
    download_generation.retrieve_db_string = Mock(return_value=generate_test_db_connection_string())
    resp = client.post(
        "/api/v2/download/transactions/",
        content_type="application/json",
        data=json.dumps({"limit": settings.MAX_DOWNLOAD_LIMIT + 1, "filters": {"award_type_codes": []}, "columns": []}),
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_download_transactions_bad_column_list_raises(client, download_test_data):
    download_generation.retrieve_db_string = Mock(return_value=generate_test_db_connection_string())
    payload = {"filters": {"award_type_codes": []}, "columns": ["modification_number", "bogus_column"]}
    resp = client.post("/api/v2/download/transactions/", content_type="application/json", data=json.dumps(payload))
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "Unknown columns" in resp.json()["detail"]
    assert "bogus_column" in resp.json()["detail"]
    assert "modification_number" not in resp.json()["detail"]


def test_download_transactions_bad_filter_type_raises(client, download_test_data):
    download_generation.retrieve_db_string = Mock(return_value=generate_test_db_connection_string())
    payload = {"filters": "01", "columns": []}
    resp = client.post("/api/v2/download/transactions/", content_type="application/json", data=json.dumps(payload))
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json()["detail"] == "Filters parameter not provided as a dict"


"""
These are intended for the experimental Elasticsearch functionality that lives alongside the Postgres
implementation. These tests verify that ES performs as expected, but that it also respects the header put in place
to trigger the experimental functionality. When ES for '/download/transactions' is used as the primary
implementation for the endpoint these tests should be updated to reflect the change.
"""


def test_es_download_transactions_without_columns(
    client, monkeypatch, download_test_data, elasticsearch_transaction_index
):
    logging_statements = []
    monkeypatch.setattr(
        "usaspending_api.download.v2.views.logger.info", lambda message: logging_statements.append(message)
    )
    monkeypatch.setattr(
        "usaspending_api.common.elasticsearch.search_wrappers.TransactionSearch._index_name",
        settings.ES_TRANSACTIONS_QUERY_ALIAS_PREFIX,
    )

    elasticsearch_transaction_index.update_index()

    download_generation.retrieve_db_string = Mock(return_value=generate_test_db_connection_string())
    resp = client.post(
        "/api/v2/download/transactions/",
        content_type="application/json",
        data=json.dumps({"filters": {"award_type_codes": []}, "columns": []}),
        **{EXPERIMENTAL_API_HEADER: ELASTICSEARCH_HEADER_VALUE},
    )

    assert resp.status_code == status.HTTP_200_OK
    assert len(logging_statements) == 1, "Expected one logging statement"
    assert (
        logging_statements[0] == "Using experimental Elasticsearch functionality for '/download/transactions'"
    ), "Expected a different logging statement"
    assert ".zip" in resp.json()["file_url"]


def test_es_download_transactions_with_columns(
    client, monkeypatch, download_test_data, elasticsearch_transaction_index
):
    logging_statements = []
    monkeypatch.setattr(
        "usaspending_api.download.v2.views.logger.info", lambda message: logging_statements.append(message)
    )
    monkeypatch.setattr(
        "usaspending_api.common.elasticsearch.search_wrappers.TransactionSearch._index_name",
        settings.ES_TRANSACTIONS_QUERY_ALIAS_PREFIX,
    )

    elasticsearch_transaction_index.update_index()

    download_generation.retrieve_db_string = Mock(return_value=generate_test_db_connection_string())
    resp = client.post(
        "/api/v2/download/transactions/",
        content_type="application/json",
        data=json.dumps(
            {
                "filters": {"award_type_codes": []},
                "columns": [
                    "assistance_transaction_unique_key",
                    "award_id_fain",
                    "modification_number",
                    "sai_number",
                    "contract_transaction_unique_key",
                ],
            }
        ),
        **{EXPERIMENTAL_API_HEADER: ELASTICSEARCH_HEADER_VALUE},
    )

    assert resp.status_code == status.HTTP_200_OK
    assert len(logging_statements) == 1, "Expected one logging statement"
    assert (
        logging_statements[0] == "Using experimental Elasticsearch functionality for '/download/transactions'"
    ), "Expected a different logging statement"
    assert ".zip" in resp.json()["file_url"]


@pytest.mark.django_db
def test_es_download_transactions_bad_limit(client, monkeypatch, elasticsearch_transaction_index):
    logging_statements = []
    monkeypatch.setattr(
        "usaspending_api.download.v2.views.logger.info", lambda message: logging_statements.append(message)
    )
    monkeypatch.setattr(
        "usaspending_api.common.elasticsearch.search_wrappers.TransactionSearch._index_name",
        settings.ES_TRANSACTIONS_QUERY_ALIAS_PREFIX,
    )

    elasticsearch_transaction_index.update_index()

    download_generation.retrieve_db_string = Mock(return_value=generate_test_db_connection_string())
    resp = client.post(
        "/api/v2/download/transactions/",
        content_type="application/json",
        data=json.dumps({"limit": "wombats", "filters": {"award_type_codes": []}, "columns": []}),
        **{EXPERIMENTAL_API_HEADER: ELASTICSEARCH_HEADER_VALUE},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert len(logging_statements) == 1, "Expected one logging statement"
    assert (
        logging_statements[0] == "Using experimental Elasticsearch functionality for '/download/transactions'"
    ), "Expected a different logging statement"


def test_es_download_transactions_excessive_limit(
    client, monkeypatch, download_test_data, elasticsearch_transaction_index
):
    logging_statements = []
    monkeypatch.setattr(
        "usaspending_api.download.v2.views.logger.info", lambda message: logging_statements.append(message)
    )
    monkeypatch.setattr(
        "usaspending_api.common.elasticsearch.search_wrappers.TransactionSearch._index_name",
        settings.ES_TRANSACTIONS_QUERY_ALIAS_PREFIX,
    )

    elasticsearch_transaction_index.update_index()

    download_generation.retrieve_db_string = Mock(return_value=generate_test_db_connection_string())
    resp = client.post(
        "/api/v2/download/transactions/",
        content_type="application/json",
        data=json.dumps({"limit": settings.MAX_DOWNLOAD_LIMIT + 1, "filters": {"award_type_codes": []}, "columns": []}),
        **{EXPERIMENTAL_API_HEADER: ELASTICSEARCH_HEADER_VALUE},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert len(logging_statements) == 1, "Expected one logging statement"
    assert (
        logging_statements[0] == "Using experimental Elasticsearch functionality for '/download/transactions'"
    ), "Expected a different logging statement"


def test_es_download_transactions_bad_column_list_raises(
    client, monkeypatch, download_test_data, elasticsearch_transaction_index
):
    logging_statements = []
    monkeypatch.setattr(
        "usaspending_api.download.v2.views.logger.info", lambda message: logging_statements.append(message)
    )
    monkeypatch.setattr(
        "usaspending_api.common.elasticsearch.search_wrappers.TransactionSearch._index_name",
        settings.ES_TRANSACTIONS_QUERY_ALIAS_PREFIX,
    )

    elasticsearch_transaction_index.update_index()

    download_generation.retrieve_db_string = Mock(return_value=generate_test_db_connection_string())
    payload = {"filters": {"award_type_codes": []}, "columns": ["modification_number", "bogus_column"]}
    resp = client.post(
        "/api/v2/download/transactions/",
        content_type="application/json",
        data=json.dumps(payload),
        **{EXPERIMENTAL_API_HEADER: ELASTICSEARCH_HEADER_VALUE},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert len(logging_statements) == 1, "Expected one logging statement"
    assert (
        logging_statements[0] == "Using experimental Elasticsearch functionality for '/download/transactions'"
    ), "Expected a different logging statement"
    assert "Unknown columns" in resp.json()["detail"]
    assert "bogus_column" in resp.json()["detail"]
    assert "modification_number" not in resp.json()["detail"]


def test_es_download_transactions_bad_filter_type_raises(
    client, monkeypatch, download_test_data, elasticsearch_transaction_index
):
    logging_statements = []
    monkeypatch.setattr(
        "usaspending_api.download.v2.views.logger.info", lambda message: logging_statements.append(message)
    )
    monkeypatch.setattr(
        "usaspending_api.common.elasticsearch.search_wrappers.TransactionSearch._index_name",
        settings.ES_TRANSACTIONS_QUERY_ALIAS_PREFIX,
    )

    elasticsearch_transaction_index.update_index()

    download_generation.retrieve_db_string = Mock(return_value=generate_test_db_connection_string())
    payload = {"filters": "01", "columns": []}
    resp = client.post(
        "/api/v2/download/transactions/",
        content_type="application/json",
        data=json.dumps(payload),
        **{EXPERIMENTAL_API_HEADER: ELASTICSEARCH_HEADER_VALUE},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert len(logging_statements) == 1, "Expected one logging statement"
    assert (
        logging_statements[0] == "Using experimental Elasticsearch functionality for '/download/transactions'"
    ), "Expected a different logging statement"
    assert resp.json()["detail"] == "Filters parameter not provided as a dict"
