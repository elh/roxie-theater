"""
Prepare processed JSON file into an import CSV for Letterboxd.
"""

import json
import argparse
from dotenv import load_dotenv
import csv
from datetime import datetime
from pytz import timezone
import os
import sys
from roxie_theater.log import JSONLogger
import time


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
    log_context["script"] = "prepare_import"

    logger = JSONLogger(**log_context)

    logger.log(message="Parsing file", file=args.file)
    with open(args.file, "r") as f:
        cal = json.load(f)
    extracted_movie_count = sum(len(m["llm"]["extracted_movies"]) for m in cal.values())
    logger.log(
        message="Parsed file", listing_count=len(cal), movie_count=extracted_movie_count
    )

    output_file = args.file.replace(".json", ".boxd.csv")
    if args.output:
        output_file = args.output
    if os.path.dirname(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as csv_file:
        # a list of tuples (first showtime, csv row)
        listings = []

        for v in cal.values():
            for m in v["llm"]["extracted_movies"]:
                # only export movies with showtimes in the future
                now = datetime.now(timezone("America/Los_Angeles"))
                last_showtime = datetime.fromisoformat(v["showtimes"][-1])
                if last_showtime < now:
                    continue

                # sorted by earliest showtime in the future
                first_showtime = next(
                    (
                        datetime.fromisoformat(s)
                        for s in v["showtimes"]
                        if datetime.fromisoformat(s) >= now
                    ),
                    None,
                )
                if not first_showtime:
                    continue

                formatted_showtime = first_showtime.strftime("Next show %B %d %I:%M%p")
                review = f"{v['title']}\n{v['link']}\n\n{formatted_showtime}"

                if "tmdb" in m and m["tmdb"]:
                    listings.append(
                        (
                            first_showtime,
                            {
                                "tmdbID": m["tmdb"]["id"],
                                "Title": m["tmdb"]["title"],
                                "Year": m["tmdb"]["release_date"][:4],
                                "Directors": m["directors"],
                                "Review": review,
                            },
                        )
                    )
                else:
                    listings.append(
                        (
                            first_showtime,
                            {
                                "tmdbID": None,
                                "Title": m["title"],
                                "Year": m["year"],
                                "Directors": m["directors"],
                                "Review": review,
                            },
                        )
                    )

        # sort by first showtime
        listings.sort(key=lambda x: x[0])

        # write csv
        fieldnames = ["tmdbID", "Title", "Year", "Directors", "Review"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for _, row in listings:
            writer.writerow(row)

    logger.log(
        message="Wrote output file",
        output_file=output_file,
        duration=time.time() - start_time,
    )


if __name__ == "__main__":
    main()
