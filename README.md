# ShotDeck Image Scraper

## Setup

### Shotstack

1. Create an account on [ShotDeck](https://shotdeck.com/)
2. Activate it
3. Note your username and password

## Install

1. Clone the repository
2. Open the terminal in the repository folder
3. Install [uv](https://github.com/astral-sh/uv)
4. Install the dependencies

```bash
uv sync
```

## Usage

Make sure you are in the repository folder, and in your terminal type:

```bash
uv run main.py --username <your_username> --password <your_password> --query <your_query> --limit <image_limit>
```

- username: your ShotDeck username
- password: your ShotDeck password
- query: your search query, comma separated tags e.g. "brad pitt, hands" or "black and white, drink"
- limit: the maximum number of images to download, as some queries return a lot of images

The images will be saved in the `downloaded_images` folder
