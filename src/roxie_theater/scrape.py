import requests
from bs4 import BeautifulSoup
import json


def main():
    url = "https://roxie.com/calendar/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    month_year = soup.select_one(".calendar-block__month-title").text.strip()
    month = month_year.split()[0]
    year = month_year.split()[1]

    movies = {}
    for day in soup.select(".calendar-day-item"):
        day_number = day.select_one(".calendar-day").text.strip()
        for film in day.select(".film"):
            link = film.select_one("a")["href"]
            title = film.select_one(".film-title").text.strip()

            showtime = film.select_one(".film-showtime").text.strip()  # e.g. "6:20 pm"

            showtime_obj = {
                "year": year,
                "month": month,
                "day": day_number,
                "showtime": showtime,
            }

            if link in movies:
                movies[link]["showtimes"].append(showtime_obj)
                continue

            movies[link] = {
                "name": title,
                "link": link,
                "showtimes": [showtime_obj],
            }

    print(json.dumps(movies, indent=2))


if __name__ == "__main__":
    main()
