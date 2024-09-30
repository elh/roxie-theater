import requests
from bs4 import BeautifulSoup
import json


def main():
    url = "https://roxie.com/calendar/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    movies = []
    for day in soup.select(".calendar-day-item"):
        day_number = day.select_one(".calendar-day").text.strip()
        for film in day.select(".film"):
            title = film.select_one(".film-title").text.strip()
            link = film.select_one(".film-title a")["href"]
            showtime = film.select_one(".film-showtime").text.strip()
            movies.append(
                {
                    "name": title,
                    "link": link,
                    "showtimes": [f"September {day_number} {showtime}"],
                }
            )

    output = {"movies": movies}
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
