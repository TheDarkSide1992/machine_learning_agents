import json
from json import JSONDecodeError

import requests

YEAR_OPERATORS = {
    "in": ":",
    "before": "<",
    "after": ">",
    "at_most": "<=",
    "at_least": ">="
}

CITATION_OPERATORS = {
    "exactly": ":",
    "less_than": "<",
    "more_than": ">",
    "at_most": "<=",
    "at_least": ">="
}


def build_filter(JsonString:str):
    paramObject = json.loads(JsonString)
    filters = []

    #Creates year filter
    if paramObject["year"] is not None:
        year_operator = YEAR_OPERATORS.get(paramObject["year_operator"])
        if year_operator == ":":
            filters.append(filters.append(f"publication_year:{paramObject["year"]}"))
        else:
            filters.append(f"publication_year:{year_operator}{paramObject["year"]}")

    if paramObject["citation_count"] is not None:
        citation_operator = CITATION_OPERATORS.get(paramObject["citation_operator"])
        if citation_operator == ":":
            filters.append(f"cited_by_count:{paramObject["citation_count"]}")
        else :
            filters.append(f"cited_by_count:{citation_operator}{paramObject['citation_count']}")

    if filters:
        return filters


def make_get_request(JsonString:str):
    """
    Makes a remote get request
    :param JsonString: a formated json object
    '{"search_query": "machine learning","citation_count": "3","year_operator": "after","year" : "2012","citation_operator": "more_than"}'
    :return:Lists of research papers in a json format
    """
    base_url = "https://api.openalex.org/works"
    paramObject = json.loads(JsonString)
    search_query = paramObject["search_query"]
    separator =","
    filter_string = separator.join(build_filter(JsonString))
    params = {}
    if filter_string:
        params = {
            "search": search_query,
            "filter": filter_string
        }
    else:
        params = {
            "search": search_query
        }
    try:
        response = requests.get(base_url, params=params)
        data = json.loads(json.dumps(response.json()))
        print(data)
    except JSONDecodeError:
        raise ValueError("Tool invariant failed: API did not return valid JSON")

    if not (200 == response.status_code):
        raise ValueError(f"Tool invariant failed: bad status {response.status_code}")

    if len(json.loads(json.dumps(data.get("results")))) == 0:
        raise ValueError("Tool invariant failed: no results found")

    return data