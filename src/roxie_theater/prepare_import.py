import json
import argparse
from dotenv import load_dotenv
import csv


def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", type=str, required=True)
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
    with open(output_file, "w") as csv_file:
        fieldnames = ["tmdbID", "Title", "Year", "Directors"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for k, v in cal.items():
            for m in v["llm"]["extracted_movies"]:
                if "tmdb" in m and m["tmdb"]:
                    writer.writerow(
                        {
                            "tmdbID": m["tmdb"]["id"],
                            "Title": m["tmdb"]["title"],
                            "Year": m["tmdb"]["release_date"][:4],
                            "Directors": m["directors"],
                        }
                    )
                else:
                    writer.writerow(
                        {
                            "tmdbID": None,
                            "Title": m["title"],
                            "Year": m["year"],
                            "Directors": m["directors"],
                        }
                    )


if __name__ == "__main__":
    main()
