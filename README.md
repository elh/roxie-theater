# roxie-theater

[![fetch](https://github.com/elh/roxie-theater/actions/workflows/fetch.yml/badge.svg)](https://github.com/elh/roxie-theater/actions/workflows/fetch.yml)

Fetches showtimes from the [Roxie Theater](https://roxie.com/calendar/) website and prepares an import for Letterboxd.

[at the Roxie](https://letterboxd.com/eugeually/list/at-the-roxie/) list will be sporadically updated with this data. Lack of Letterboxd API means this needs to be done manually or with browser automation.

## Implementation

```mermaid
graph TD;
    bs4["scrape.py (bs4)"];
    gpt["llm_extract.py (GPT)"];
    tmdb["id_movies.py (TMDB)"];
    out["prepare_import.py"];

    style OUT fill-opacity:0, stroke-opacity:0;

    bs4--json-->gpt--json-->tmdb--json-->out--csv-->OUT[ ];
```

See [`fetch`](.github/workflows/fetch.yml) Github Action for cron.<br>
Relies on GPT and TMDB APIs.<br>
`OPENAI_API_KEY` and `TMDB_TOKEN` env vars required.<br>
Python and deps managed with Rye.

<br>
<br>

## Disclaimer

Unofficial project from a Roxie Theater and Letterboxd fan.
