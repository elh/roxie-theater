"""
Use GPT to extract movie information from the listing webpages.
"""

import os
import sys
import json
import argparse
from datetime import datetime
import time
import random
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field

MODEL = "gpt-4o-mini"

SYS_PROMPT = """\
Given this theater movie listing, read the page and extract the movies being shown.
For each movie, extract the title, directors, and release year.
Return the final result as a JSON object with a `movies` array (`title`, `directors`, `year`, `is_short_film` keys).

Some possible cases to consider:
* The listing is for a single movie. This is the common case. Return a list with a single movie.
* The listing is for a special event like a party and does not contain individually credited movies. Return an empty list.
* The listing is for a special event with multiple movies like a double feature. Return a list with all the movies.
* The listing includes some extra context in the title that should be stripped out. For example, "Staff Pick: The Matrix". Return the title as "The Matrix".

Make sure to only include movies that are being shown, not just movies passively mentioned on the page.
"""


class ExtractedMovies(BaseModel):
    class Movie(BaseModel):
        title: str = Field(description="Movie title")
        directors: str = Field(description="Movie directors")
        year: int = Field(description="Release year")
        is_short_film: bool = Field(description="Is short film")

    movies: list[Movie]


CHAT_DEFAULTS = defaults = {
    "model": "gpt-4o-mini",
    "temperature": 0,
}


def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")


def process_movie(client: OpenAI, movie: dict) -> list:
    input = {
        "page_title": movie["title"],
        "page_year": movie["year"],
        "page_directors": movie["directors"],
        "page_content": movie["content"],
    }

    args = CHAT_DEFAULTS | {
        "messages": [
            {"role": "system", "content": SYS_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    input, indent=2, ensure_ascii=False, default=datetime_serializer
                ),
            },
        ],
        "response_format": ExtractedMovies,
    }

    response = client.beta.chat.completions.parse(**args)
    if len(response.choices) == 0:
        raise ValueError("No completions returned")
    out = response.choices[0].message.parsed

    return {
        "extracted_movies": [m.dict() for m in out.movies],
    }


def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, required=True)
    parser.add_argument("-o", "--output", type=str, help="output path")
    parser.add_argument("-v", "--verbose", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("OPENAI_API_KEY env var required")
        sys.exit(1)

    client = OpenAI(api_key=openai_api_key)

    if args.verbose:
        print("Parsing file ...")
    with open(args.file, "r") as f:
        cal = json.load(f)

    for index, k in enumerate(cal):
        v = cal[k]
        if args.verbose:
            print(f"Processing movie: {v['title']} ({index + 1} of {len(cal)}) ...")
        processed = process_movie(client, v)
        if args.verbose:
            print(f"Processed movie: {len(processed['extracted_movies'])} extracted")
        cal[k]["llm"] = processed

        # sleep w/ jitter
        time.sleep(random.uniform(0.05, 0.1))

    if args.verbose:
        extracted_movie_count = sum(
            len(m["llm"]["extracted_movies"]) for m in cal.values()
        )
        print(f"Extracted {extracted_movie_count} movies from {len(cal)} listings")

    # save results
    output_file = args.file.replace(".json", ".llm.json")
    if args.output:
        output_file = args.output
    if os.path.dirname(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        # NOTE: not ascii
        json.dump(cal, f, indent=2, ensure_ascii=False, default=datetime_serializer)


if __name__ == "__main__":
    main()
