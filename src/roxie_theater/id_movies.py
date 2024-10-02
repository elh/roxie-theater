"""
Find canonical TMDB ids for extracted movies.
"""

import os
import sys
import json
import argparse
from datetime import datetime
import time
import random
import copy
from dotenv import load_dotenv
import requests
from roxie_theater.log import Logger, JSONLogger, log_func


def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")


@log_func()
def identify_movies(
    tmdb_token: str,
    extracted_movies: list[dict],
    logger: Logger = JSONLogger(),
) -> list[dict]:
    base_url = "https://api.themoviedb.org/"
    endpoint = "/3/search/movie"
    url = requests.compat.urljoin(base_url, endpoint)

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {tmdb_token}",
    }

    # mutate and return a copy
    out = copy.deepcopy(extracted_movies)
    for m in out:
        params = {"query": m["title"], "year": m["year"]}
        retry_count = 0
        while retry_count < 3:
            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 429:
                logger.log(message="Rate limited")
                time.sleep(10)
                retry_count += 1
                continue
            if response.status_code != 200:
                logger.log(
                    message="Error",
                    error="failed TMDB search",
                    status_code=response.status_code,
                )
                break

            data = response.json()
            logger.log(
                message="TMDB search",
                title=m["title"],
                year=m["year"],
                result_count=len(data["results"]),
            )
            if len(data["results"]) > 0:
                m["tmdb"] = data["results"][0]
            else:
                m["tmdb"] = None
            break
        else:
            logger.log(message="Error", error="failed TMDB search. Retries exhausted")
            m["tmdb"] = None

    return out


def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, required=True)
    parser.add_argument("-o", "--output", type=str, help="output path")
    parser.add_argument(
        "-l",
        "--log-context",
        type=str,
        help="metadata to include in all logs. as JSON dict",
    )
    args = parser.parse_args()

    start_time = time.time()

    log_context = {}
    if args.log_context:
        try:
            log_context = json.loads(args.log_context)
        except json.JSONDecodeError:
            print("Invalid JSON for --log-context")
            sys.exit(1)
    log_context["script"] = "id_movies"

    logger = JSONLogger(**log_context)

    tmdb_token = os.environ.get("TMDB_TOKEN")
    if not tmdb_token:
        logger(message="Error", error="TMDB_TOKEN env var required")
        sys.exit(1)

    logger.log(message="Parsing file", file=args.file)
    with open(args.file, "r") as f:
        cal = json.load(f)
    extracted_movie_count = sum(len(m["llm"]["extracted_movies"]) for m in cal.values())
    logger.log(
        message="Parsed file", listing_count=len(cal), movie_count=extracted_movie_count
    )

    for index, k in enumerate(cal):
        v = cal[k]

        movie_logger = logger.with_kwargs(listing=v["title"], index=index)
        out = identify_movies(
            tmdb_token,
            v["llm"]["extracted_movies"],
            logger=movie_logger,
        )
        movie_logger.log(
            message="Identified movies",
            identified_count=sum(
                [1 if ("tmdb" in m and m["tmdb"]) else 0 for m in out]
            ),
            count=len(out),
        )
        cal[k]["llm"]["extracted_movies"] = out

        # sleep w/ jitter
        time.sleep(random.uniform(0.05, 0.2))

    # save results
    output_file = args.file.replace(".json", ".tmdb.json")
    if args.output:
        output_file = args.output
    if os.path.dirname(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        # NOTE: not ascii
        json.dump(cal, f, indent=2, ensure_ascii=False, default=datetime_serializer)
    logger.log(
        message="Wrote output file",
        output_file=output_file,
        duration=time.time() - start_time,
    )


if __name__ == "__main__":
    main()
