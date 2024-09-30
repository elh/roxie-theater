# roxie-theater

```mermaid
graph TD;
    bs4["scrape.py (bs4)"];
    gpt["llm_extract.py (GPT)"];
    tmdb["id_movies.py (TMDB)"];
    out["prepare_import.py"];

    style OUT fill-opacity:0, stroke-opacity:0;

    bs4--json-->gpt--json-->tmdb--json-->out--csv-->OUT[ ];
```
