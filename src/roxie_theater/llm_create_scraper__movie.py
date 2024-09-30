import os
import sys
from dotenv import load_dotenv
from scrapegraphai.graphs import ScriptCreatorGraph
from pydantic import BaseModel, Field

URL = "https://roxie.com/film/staff-pick-institute-benjamenta-35mm/"

PROMPT = """\
Review the following movie webpage for a theater and extract the name of the movie, year, and director(s).
"""


class Movie(BaseModel):
    name: str = Field(description="Name of the movie")
    year: int = Field(description="Year the movie was released")
    directors: list[str] = Field(description="List of directors of the movie")


def main():
    load_dotenv()
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("OPENAI_API_KEY env var required")
        sys.exit(1)

    graph_config = {
        "llm": {
            "api_key": openai_api_key,
            "model": "openai/gpt-4o",
        },
        "library": "BeautifulSoup",
        "verbose": True,
        "headless": False,
    }

    graph = ScriptCreatorGraph(
        prompt=PROMPT,
        source=URL,
        config=graph_config,
        schema=Movie,
    )

    result = graph.run()
    print(result)


if __name__ == "__main__":
    main()
