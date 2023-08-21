import os
import time

import requests
import shutil
from git import Repo
import logging
import json
from ccscanner import scanner
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
from concurrent.futures import ThreadPoolExecutor

# Create a custom logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create handlers
f_handler = logging.FileHandler('file.log', mode='w')
f_handler.setLevel(logging.INFO)

# Create formatters and add it to handlers
f_format = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s')
f_handler.setFormatter(f_format)

# Add handlers to the logger
logger.addHandler(f_handler)


def save_js(content, path):
    with open(path, 'w') as save_f:
        json.dump(content, save_f)


def make_query(after_cursor=None, star_range=">3000", lang="C++"):
    return """
query {
  search(query: "language:LANG stars:RANGE", type: REPOSITORY, first: 100, after:AFTER) {
    repositoryCount
    edges {
      node {
        ... on Repository {
          nameWithOwner
          url
          stargazerCount
        }
      }
    }    
    pageInfo {
      endCursor
      hasNextPage
    }
  }
}
""".replace(
        "AFTER", '"{}"'.format(after_cursor) if after_cursor else "null"
    ).replace("LANG", '{}'.format(lang)).replace("RANGE", str(star_range))


def get_response(url, headers, language, star_range_str, curr_cursor):
    while True:
        try:
            logger.info(f"Querying Language:{language}, Range: {star_range_str}, Cursor:{curr_cursor}")
            response = requests.post(url, json={"query": make_query(lang=language, star_range=star_range_str,
                                                                    after_cursor=curr_cursor)}, headers=headers)
            response.raise_for_status()
            return response.json()
        except (HTTPError, ConnectionError, Timeout, RequestException) as error:
            logger.error(f"Request failed due to {type(error).__name__}: {error}")


def clone_and_scan_repo(repo):
    name = repo["node"]["nameWithOwner"].replace("/", "@@")
    r_url = repo["node"]["url"]
    stars = repo["node"]["stargazerCount"]
    if not os.path.isdir(name):
        attempt = 0
        # Attempt to re-download repositories if network errors occurs
        while attempt < 10:
            try:
                logger.info(f"Cloning {name} ({stars} stars) from {r_url} (attempt: {attempt})")
                Repo.clone_from(r_url, name, multi_options=["--depth 1"])
                break
            except Exception as e:
                logger.error(f"Failed to clone repo: {e}")
                attempt = attempt + 1
                # Sleep thread to avoid thrashing
                time.sleep(10 * attempt)

    logger.info(f"Scanning {name} ({stars} stars)")
    ccscan = scanner.scanner(name)
    res = json.loads(json.dumps(ccscan, default=lambda o: o.__dict__))
    save_js(res, os.path.join("results/", name) + ".json")
    # Remove scanned repository
    shutil.rmtree(name)

# Query API for repositories within a star range
def find_repos(url, headers, language, star_range, executor, curr_cursor=None):
    has_next_page = True
    while has_next_page:
        # Query API for repositories in star range
        response = get_response(url, headers, language, star_range, curr_cursor)

        has_next_page = response["data"]["search"]["pageInfo"]["hasNextPage"]
        # get next page cursor for pagination
        curr_cursor = response["data"]["search"]["pageInfo"]["endCursor"]
        data = response["data"]["search"]["edges"]
        # submit clone and scan job to thread pool for each repository
        for repo in data:
            executor.submit(clone_and_scan_repo, repo)


def main(token, url, languages):
    headers = {"Authorization": f"Bearer {token}"}
    # Initialise thread pool with cpu_count number of workers
    with ThreadPoolExecutor() as executor:
        # Search schedule needed to overcome API limitations and rate limiting
        for language in languages:
            star_greater = ">3000"
            find_repos(url, headers, language, star_greater, executor)
            for star_count in range(3000, 500, -100):
                range_query = f"{star_count - 99}..{star_count}"
                find_repos(url, headers, language, range_query, executor)
            for star_count in range(500, 150, -10):
                range_query = f"{star_count - 9}..{star_count}"
                find_repos(url, headers, language, range_query, executor)
            for star_count in range(150, 100, -1):
                find_repos(url, headers, language, str(star_count), executor)


if __name__ == '__main__':
    # set the GITHUB_TOKEN environment variable to run tool.
    token = os.environ.get('GITHUB_TOKEN')
    # api endpoint
    url = "https://api.github.com/graphql"
    # languages to select repositories from.
    languages = ["C++", "C"]
    main(token, url, languages)
