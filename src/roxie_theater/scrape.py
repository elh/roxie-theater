import os
import json
import argparse
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import time
import random

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

            showtime_datetime = parse_showtime(year, month, day, showtime)

            if link in calendar:
                calendar[link]["showtimes"].append(showtime_datetime)
                continue

            calendar[link] = {
                "title": title,
                "link": link,
                "showtimes": [showtime_datetime],
            }

    return calendar


def parse_movie(url: str) -> dict:
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
    parser.add_argument("-v", "--verbose", action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    if args.verbose:
        print("Scraping calendar ...")
    cal = scrape_calendar()

    print(f"Scraped calendar with {len(cal)} distinct movies")

    for index, k in enumerate(cal):
        v = cal[k]
        if args.verbose:
            print(f"Scraping movie: {v['title']} ({index + 1} of {len(cal)}) ...")
        movie = parse_movie(v["link"])
        cal[k].update(movie)

        # sleep w/ jitter
        time.sleep(random.uniform(0.25, 1))

    # save results
    output_file = f"output/data.{int(time.time())}.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        # NOTE: not ascii
        json.dump(cal, f, indent=2, ensure_ascii=False, default=datetime_serializer)


if __name__ == "__main__":
    main()
