import json
import argparse
from dotenv import load_dotenv
import csv
from datetime import datetime
from pytz import timezone
import os


def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, required=True)
    parser.add_argument("-o", "--output", type=str, help="output path")
    parser.add_argument("-v", "--verbose", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

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

    output_file = args.file.replace(".json", ".boxd.csv")
    if args.output:
        output_file = args.output
    if os.path.dirname(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as csv_file:
        fieldnames = ["tmdbID", "Title", "Year", "Directors", "Review"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for v in cal.values():
            for m in v["llm"]["extracted_movies"]:
                first_showtime = datetime.fromisoformat(v["showtimes"][0])
                last_showtime = datetime.fromisoformat(v["showtimes"][-1])

                # only export movies with showtimes in the future
                if last_showtime < datetime.now(timezone("America/Los_Angeles")):
                    continue

                formatted_showtime = first_showtime.strftime("First show %B %d %I:%M%p")
                review = f"{v['title']}\n{v['link']}\n\n{formatted_showtime}"

                if "tmdb" in m and m["tmdb"]:
                    writer.writerow(
                        {
                            "tmdbID": m["tmdb"]["id"],
                            "Title": m["tmdb"]["title"],
                            "Year": m["tmdb"]["release_date"][:4],
                            "Directors": m["directors"],
                            "Review": review,
                        }
                    )
                else:
                    writer.writerow(
                        {
                            "tmdbID": None,
                            "Title": m["title"],
                            "Year": m["year"],
                            "Directors": m["directors"],
                            "Review": review,
                        }
                    )


if __name__ == "__main__":
    main()
