# ICO Decision Notice Agentic RAG

## Scraper

This project contains a Python script to scrape decision notices from the UK's Information Commissioner's Office (ICO) website.

## How to Run

### 1. Setup

It is recommended to use a Python virtual environment to manage dependencies.

Install the necessary libraries using pip:

```bash
pip install requests beautifulsoup4
```

### 2. Execution

To run the scraper, execute the following command from the root directory of this project:

```bash
python scraper/scraper.py
```

The script will start fetching data from the ICO website's API, processing each decision notice, and downloading the associated PDF.

### 3. Output

The scraped data is stored in the `data/` directory. Each decision notice is saved in its own numbered sub-folder (e.g., `case-1`, `case-2`, etc.).

Each case folder contains:

- `metadata.txt`: A text file containing the key metadata for the decision notice, such as Organisation, Date, Sector, Decision, and Abstract.
- A `.pdf` file: The full decision notice document downloaded from the ICO website.
