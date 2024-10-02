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
from roxie_theater.log import JSONLogger, log_func

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


@log_func()
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
    parser.add_argument(
        "-l",
        "--log-context",
        type=str,
        help="metadata to include in all logs. as JSON object",
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
    log_context["script"] = "llm_extract"

    logger = JSONLogger(**log_context)

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        logger(message="Error", error="OPENAI_API_KEY env var required")
        sys.exit(1)

    client = OpenAI(api_key=openai_api_key)

    with open(args.file, "r") as f:
        cal = json.load(f)

    for index, k in enumerate(cal):
        v = cal[k]

        movie_logger = logger.with_kwargs(listing=v["title"], index=index)
        processed = process_movie(client, movie=v, logger=movie_logger)
        movie_logger.log(
            message="Processed movie",
            extracted_count=len(processed["extracted_movies"]),
        )
        cal[k]["llm"] = processed

        # sleep w/ jitter
        time.sleep(random.uniform(0.05, 0.1))

    logger.log(
        message="Processed all movies",
        listing_count=len(cal),
        extracted_movie_count=sum(
            len(m["llm"]["extracted_movies"]) for m in cal.values()
        ),
    )

    # save results
    output_file = args.file.replace(".json", ".llm.json")
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
