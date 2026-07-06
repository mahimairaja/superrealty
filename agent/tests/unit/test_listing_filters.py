from src.agents.listing_filters import (
    ListingSearchFilters,
    filter_listings,
    summarize_filters,
)

CATALOG = [
    {
        "code": "A",
        "address": "1 Main St, Sarnia",
        "beds": 2,
        "baths": 1,
        "price": 400000,
        "sqft": 900,
        "area": "Sarnia",
    },
    {
        "code": "B",
        "address": "2 Oak Ave, Sarnia",
        "beds": 3,
        "baths": 2,
        "price": 480000,
        "sqft": 1400,
        "area": "Sarnia",
    },
    {
        "code": "C",
        "address": "9 Lake Rd, Bright's Grove",
        "beds": 4,
        "baths": 3,
        "price": 720000,
        "sqft": 2200,
        "area": "Bright's Grove",
    },
    {
        "code": "D",
        "address": "5 Elm St, Sarnia",
        "beds": 3,
        "baths": None,
        "price": None,
        "sqft": None,
        "area": "Sarnia",
    },
]


def test_empty_filter_returns_the_whole_catalog():
    assert filter_listings(CATALOG, ListingSearchFilters()) == CATALOG
    assert ListingSearchFilters().is_empty()


def test_min_beds_and_area():
    out = filter_listings(CATALOG, ListingSearchFilters(min_beds=3, area="Sarnia"))
    assert {h["code"] for h in out} == {"B", "D"}  # 3+ beds AND in Sarnia (not C)


def test_max_price_excludes_unknown_price():
    # D has no price, so a budget filter cannot confirm it fits and drops it.
    out = filter_listings(CATALOG, ListingSearchFilters(max_price=500000))
    assert {h["code"] for h in out} == {"A", "B"}


def test_price_range_and_sqft():
    out = filter_listings(
        CATALOG, ListingSearchFilters(min_price=450000, max_price=800000, min_sqft=1500)
    )
    assert {h["code"] for h in out} == {"C"}  # B is under 1500 sqft


def test_sort_by_price_desc():
    out = filter_listings(
        CATALOG, ListingSearchFilters(sort_by="price", sort_order="desc")
    )
    prices = [h["code"] for h in out]
    assert prices[0] == "C" and prices[-1] == "D"  # highest first, unknown last


def test_unknown_sort_is_dropped_not_raised():
    f = ListingSearchFilters(sort_by="banana", sort_order="sideways")
    assert f.sort_by is None and f.sort_order is None  # whitelisted, warned, no raise


def test_inverted_price_range_is_dropped():
    f = ListingSearchFilters(min_price=800000, max_price=400000)
    assert f.min_price is None and f.max_price is None


def test_empty_area_becomes_none_and_sort_order_needs_a_field():
    assert ListingSearchFilters(area="   ").area is None
    # A sort order with nothing to sort by is meaningless -> dropped.
    assert ListingSearchFilters(sort_order="asc").sort_order is None


def test_summarize_filters_reads_back_criteria():
    f = ListingSearchFilters(area="Sarnia", min_beds=3, max_price=480000)
    assert summarize_filters(f) == "in Sarnia, 3+ beds, under $480,000"
    assert summarize_filters(ListingSearchFilters()) == ""
    lo_hi = ListingSearchFilters(min_price=300000, max_price=500000)
    assert summarize_filters(lo_hi) == "$300,000-$500,000"
