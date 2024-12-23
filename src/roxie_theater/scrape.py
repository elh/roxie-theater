"""
Fetch Roxie Theater showtimes from listing webpages using BeautifulSoup and requests.
"""

import os
import sys
import json
import argparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import time
import random
from roxie_theater.log import JSONLogger, log_func

la_timezone = pytz.timezone("America/Los_Angeles")
calendar_url = "https://roxie.com/calendar/"


def parse_showtime(year: str, month: str, day: str, showtime: str) -> datetime:
    date_str = f"{year} {month} {day} {showtime}"
    dt = datetime.strptime(date_str, "%Y %m %d %I:%M %p")
    return la_timezone.localize(dt)


def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError("Type not serializable")


@log_func()
def scrape_calendar() -> dict:
    response = requests.get(calendar_url)
    soup = BeautifulSoup(response.content, "html.parser")

    month_year_str = soup.select_one(".calendar-block__month-title").text.strip()
    month = datetime.strptime(month_year_str.split()[0], "%B").month
    year = int(month_year_str.split()[1])

    calendar = {}
    prior_day = None
    for day_div in soup.select(".calendar-day-item"):
        day = int(day_div.select_one(".calendar-day").text.strip())
        if prior_day is not None and day < prior_day:
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1
        prior_day = day

        for film in day_div.select(".film"):
            link = film.select_one("a")["href"]
            title = film.select_one(".film-title").text.strip()
            showtime = film.select_one(".film-showtime").text.strip()

            showtime_datetime_str = parse_showtime(
                year, month, day, showtime
            ).isoformat()

            if link in calendar:
                calendar[link]["showtimes"].append(showtime_datetime_str)
                continue

            calendar[link] = {
                "title": title,
                "link": link,
                "showtimes": [showtime_datetime_str],
            }

    return calendar


@log_func(kwarg_keys=["url"])
def scrape_movie_page(url: str) -> dict:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    year = None
    year_node = soup.find(
        "h5", class_="content-film__film-details-title", string="Year"
    )
    if year_node:
        year = int(year_node.next_sibling.strip())

    directors = None
    directors_node = soup.find(
        "h5", class_="content-film__film-details-title", string="Director"
    )
    if directors_node:
        directors = directors_node.next_sibling.strip()

    content = None
    content_node = soup.find("div", class_="content-film__content content")
    if content_node:
        content = content_node.decode_contents()

    return {
        "year": year,
        "directors": directors,
        "content": content,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", type=str, help="output path")
    parser.add_argument(
        "-p", "--prior-output-file", type=str, help="prior output json file path"
    )
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
    log_context["script"] = "scrape"

    logger = JSONLogger(**log_context)

    prior_output = None
    if args.prior_output_file:
        with open(args.prior_output_file, "r") as f:
            prior_output = json.load(f)

    cal = scrape_calendar(logger=logger)
    logger.log(message="Scraped calendar", listing_count=len(cal))

    for index, k in enumerate(cal):
        v = cal[k]
        movie_logger = logger.with_kwargs(listing=v["title"], index=index)

        if prior_output and k in prior_output:
            movie_logger.log(message="Skipping movie in prior output")
            new_showtimes = cal[k]["showtimes"]
            cal[k].update(prior_output[k])
            for showtime in new_showtimes:
                if showtime not in cal[k]["showtimes"]:
                    cal[k]["showtimes"].append(showtime)
            cal[k]["showtimes"] = sorted(cal[k]["showtimes"])
            continue

        movie = scrape_movie_page(url=v["link"], logger=movie_logger)
        cal[k].update(movie)

        # sleep w/ jitter
        time.sleep(random.uniform(0.25, 1))

    # save results
    output_file = f"output/data.{int(time.time())}.json"
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
