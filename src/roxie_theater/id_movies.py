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


def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")


def identify_movies(
    tmdb_token: str, extracted_movies: list[dict], verbose: bool = False
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
                print("Error: Rate limited")
                print("Sleeping for 10 seconds")
                time.sleep(10)
                retry_count += 1
                continue
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                break

            data = response.json()
            if verbose:
                print(
                    f"\t\t\tFound {len(data['results'])} result(s) for {m['title']} - {m['year']}"
                )
            if len(data["results"]) > 0:
                m["tmdb"] = data["results"][0]
            else:
                m["tmdb"] = None
            break
        else:
            print(f"Failed to get data for {m['title']} after 3 retries")
            m["tmdb"] = None

    return out


def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, required=True)
    parser.add_argument("-o", "--output", type=str, help="output path")
    parser.add_argument("-v", "--verbose", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    tmdb_token = os.environ.get("TMDB_TOKEN")
    if not tmdb_token:
        print("TMDB_TOKEN env var required")
        sys.exit(1)

    if args.verbose:
        print("Parsing file ...")
    with open(args.file, "r") as f:
        cal = json.load(f)
    if args.verbose:
        print(f"Parsed file with {len(cal)} listings")
        extracted_movie_count = sum(
            len(m["llm"]["extracted_movies"]) for m in cal.values()
        )
        print(f"Parsed file with {extracted_movie_count} extracted movies")

    for index, k in enumerate(cal):
        v = cal[k]
        if args.verbose:
            print(
                f"Identifying movies:\t{v['title']} ({len(v['llm']['extracted_movies'])} movies) ({index + 1} of {len(cal)}) ..."
            )
        out = identify_movies(
            tmdb_token, v["llm"]["extracted_movies"], verbose=args.verbose
        )
        if args.verbose:
            print(
                f"\t\t\tIdentified {sum([1 if ('tmdb'in m and m['tmdb']) else 0 for m in out])} of {len(out)} movies"
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


if __name__ == "__main__":
    main()
