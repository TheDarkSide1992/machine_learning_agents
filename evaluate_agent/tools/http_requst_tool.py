import json
from json import JSONDecodeError

import requests

YEAR_OPERATORS = {
    "in": ":",
    "before": "<",
    "after": ">",
}

CITATION_OPERATORS = {
    "exactly": ":",
    "less_than": "<",
    "more_than": ">",
}


def build_filter(JsonString:str) -> list[str] :
    paramObject = json.loads(JsonString)
    filters = []

    #Creates year filter
    if "publication_year" in paramObject and paramObject["publication_year"] != "":
        year_operator = YEAR_OPERATORS.get(paramObject["year_operator"])
        if year_operator == ":":
            filters.append(filters.append(f"publication_year:{paramObject["publication_year"]}"))
        else:
            filters.append(f"publication_year:{year_operator}{paramObject["publication_year"]}")

    # Creates citation filter
    if "citation_count" in paramObject and paramObject["citation_count"] != "":
        citation_operator = CITATION_OPERATORS.get(paramObject["citation_operator"])
        if citation_operator == ":":
            filters.append(f"cited_by_count:{paramObject["citation_count"]}")
        else :
            filters.append(f"cited_by_count:{citation_operator}{paramObject["citation_count"]}")

    return filters


def make_get_request(JsonString:str):
    """
    Makes a remote get request
    :param JsonString: a formated json object
    '{"search_query": "machine learning","citation_count": "3","year_operator": "after","year" : "2012","citation_operator": "more_than"}'
    :return:Lists of research papers in a json format
    """
    base_url = "https://api.openalex.org/works"

    # builds the parameters for the request
    paramObject = json.loads(JsonString)
    search_query = ""
    if "search_query" in paramObject:
        search_query = paramObject["search_query"]
    separator =","
    filter_string = ""
    if ("publication_year" in paramObject and paramObject["publication_year"] != "") or ("citation_count" in paramObject and paramObject["citation_count"] != ""):
        filter_segments = build_filter(JsonString)
        if len(filter_segments) > 1:
            string_segments = [str(segment) for segment in filter_segments]
            filter_string = separator.join(string_segments)
        else:
            filter_string = filter_segments
    params = {}
    if filter_string and search_query:
        params = {
            "search": search_query,
            "filter": filter_string
        }
    # Try the request
    try:
        response = requests.get(base_url, params=params)
        data = json.loads(json.dumps(response.json()))
        works = data["results"]
        minimal_works = []
        # Removes not needed data from the response
        for work in works:
            all_authors = []
            authorships = work.get('authorships', [])
            for authorship in authorships:
                author_info = authorship.get('author')
                if author_info and 'display_name' in author_info:
                    all_authors.append(author_info['display_name'])

            minimalised_work = {
                "title": work.get('title'),
                "authors": all_authors,
                "citations": work.get('cited_by_count'),
                "publication_year": work.get('publication_year'),
                "url": work.get('id'),
                "relevance_score": work.get('relevance_score')
            }
            minimal_works.append(minimalised_work)
    # throws different exceptions depending on the error
    except JSONDecodeError:
        raise ValueError("Tool invariant failed: API did not return valid JSON")

    if not (200 == response.status_code):
        raise ValueError(f"Tool invariant failed: bad status {response.status_code}")

    if len(json.loads(json.dumps(data.get("results")))) == 0:
        raise ValueError("Tool invariant failed: no results found")

    # Returns a string json object containing the minimal works
    return json.dumps(minimal_works)