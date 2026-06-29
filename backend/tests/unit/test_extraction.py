"""Unit tests for the listing extraction ladder, against saved fixtures (no network)."""

from pathlib import Path

from src.services.extraction_service import extract_from_csv, extract_from_html

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_jsonld_extraction():
    listings = extract_from_html(_read("jsonld.html"))
    assert len(listings) == 1
    home = listings[0]
    assert "123 Maple Street" in home["address"]
    assert home["price"] == 450000.0
    assert home["beds"] == 3
    assert home["baths"] == 2.0
    assert home["sqft"] == 1500
    assert home["area"] == "Sarnia"
    assert home["code"] == "L-001"


def test_opengraph_extraction():
    listings = extract_from_html(_read("opengraph.html"))
    assert len(listings) == 1
    home = listings[0]
    assert home["address"] == "456 Oak Avenue, Sarnia"
    assert "4 bedroom" in home["description"]
    assert home["image_url"] == "https://example.com/oak.jpg"
    assert home["price"] == 525000.0


def test_dom_heuristics_extraction():
    listings = extract_from_html(_read("plain.html"))
    assert len(listings) == 1
    home = listings[0]
    assert "789 Pine Road" in home["address"]
    assert home["price"] == 399000.0
    assert home["beds"] == 2


def test_csv_extraction():
    listings = extract_from_csv(_read("listings.csv"))
    assert len(listings) == 2
    assert listings[0]["address"] == "11 King St Sarnia"
    assert listings[0]["price"] == 350000.0
    assert listings[1]["beds"] == 3


def test_llm_backstop_used_when_no_structured_data():
    calls: list[str] = []

    def fake_llm(text: str):
        calls.append(text)
        return [{"address": "321 Birch Lane, Sarnia", "price": 475000, "beds": 3}]

    listings = extract_from_html(_read("nostructure.html"), llm=fake_llm)
    assert calls, "llm backstop was not called"
    assert "Birch Lane" in calls[0]
    assert listings[0]["address"] == "321 Birch Lane, Sarnia"
    assert listings[0]["price"] == 475000.0


def test_ladder_prefers_structured_over_llm():
    def boom(text: str):
        raise AssertionError("llm must not be called when structured data exists")

    listings = extract_from_html(_read("jsonld.html"), llm=boom)
    assert listings[0]["price"] == 450000.0
