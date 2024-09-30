import os
import sys
from dotenv import load_dotenv
from scrapegraphai.graphs import ScriptCreatorGraph
from pydantic import BaseModel, Field

URL = "https://roxie.com/calendar/"

PROMPT = """\
Review the following movie showtimes and extract a list of all the movies and their showtimes.
"""


class Movie(BaseModel):
    name: str = Field(description="Name of the movie")
    link: str = Field(description="Link to the movie from the website")
    showtimes: list[str] = Field(
        description="List of showtimes formatted like 'September 1 12:30 PM' or 'September 15 7:15 PM'"
    )


class Movies(BaseModel):
    movies: list[Movie] = Field(description="Name of the movie")


def main():
    load_dotenv()
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("OPENAI_API_KEY env var required")
        sys.exit(1)

    graph_config = {
        "llm": {
            "api_key": openai_api_key,
            "model": "openai/gpt-4o-mini",
        },
        "library": "BeautifulSoup",
        "verbose": True,
        "headless": False,
    }

    graph = ScriptCreatorGraph(
        prompt=PROMPT,
        source=URL,
        config=graph_config,
        schema=Movies,
    )

    result = graph.run()
    print(result)


if __name__ == "__main__":
    main()
