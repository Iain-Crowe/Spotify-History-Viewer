# === IMPORTS ==================================================================
from __future__ import annotations

from datetime import datetime
import json
import logging
import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List

# === LOGGING CODE =============================================================
# ANSI escape codes for colors
RESET = "\033[0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BOLD_BLUE = "\033[1m\033[34m"
CYAN = "\033[36m"
BOLD_RED = "\033[1m\033[31m"

# Logger, use `init_logger()` before using elsewhere
logger = logging.getLogger(__name__)


class LogFormatter(logging.Formatter):
    def format(self, record):
        log_colors = {
            logging.DEBUG: CYAN,
            logging.INFO: GREEN,
            logging.WARNING: YELLOW,
            logging.ERROR: RED,
            logging.CRITICAL: BOLD_RED,
        }
        color = log_colors.get(record.levelno, RESET)
        record.asctime = f"{BOLD_BLUE}{self.formatTime(record, self.datefmt)}{RESET}"
        record.levelname = f"{color}{record.levelname}{RESET}"
        return f"{record.asctime}: {record.levelname} - {record.msg}"


def init_logger() -> None:
    """
    Initialize the logger using custom `LogFormatter`
    """
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    formatter = LogFormatter(
        "%(asctime)s: %(levelname)s - %(message)s", datefmt="%H:%M:%S %Y-%m-%d"
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)


# === FILE LOADING AND VALIDATION CODE =========================================
# Template for validation.
TEMPLATE = [{"endTime": "", "artistName": "", "trackName": "", "msPlayed": 0}]


def _read_file(file_path: str) -> Any | None:
    """
    Private method to read JSON file.

    Params -
        `file_path`: Path to target JSON file.

    Returns data from JSON file if possible.
    """
    logger.info(f"Attempting to read from '{file_path}'...")
    try:
        with open(file_path, "r", encoding='utf-8') as file:
            data = json.load(file)
            logger.info(f"Successfully read JSON data from '{file_path}'.")
            return data
    except FileNotFoundError:
        logger.error(f"The file '{file_path}' was not found.")
    except json.JSONDecodeError:
        logger.error(f"The file contains invalid JSON.")
    except Exception as e:
        logger.error(f"An unexpected error occured: {e}")

    return None


def validate_content(
    content: List[Dict[str, Any]], template: List[Dict[str, Any]]
) -> bool:
    """
    Validation method to ensure the JSON file contains the necessary data.

    Params -
        `content`: Unvalidated JSON data read from `_read_file()`.
        `template`: Template object to check `content` against, use `TEMPLATE`.

    Returns a `bool`. `True` if `content` matches `template`, `False` otherwise.
    """
    if not content or not template:
        logger.error("Content or template is empty.")
        return False

    template_keys = set(template[0].keys())
    for index, entry in enumerate(content):
        entry_keys = set(entry.keys())
        if entry_keys != template_keys:
            logger.error(f"Entry {index} keys do not match template keys.")
            return False
        for key in template_keys:
            if type(entry[key]) != type(template[0][key]):
                logger.error(
                    f"Entry {index} key '{key}' type mismatch (Expected '{type(template[0][key])}', Recieved '{type(entry[key])}')."
                )
                return False

    logger.info("Content matches template.")
    return True


def get_data(file_path: str) -> List[Dict[str, Any]] | None:
    """
    Gets the data from a JSON file and returns it if content is correctly formatted.

    Params:
        `file_path` - Path to target JSON file.

    Returns content at `file_path` if content is formatted correctly and `None` otherwise.
    """
    content = _read_file(file_path)

    if not content:
        return None

    if validate_content(content, TEMPLATE):
        logger.info(f"Loaded content from '{file_path}'.")
        return content
    else:
        logger.error(f"Could not load '{file_path}'.")
        return None


# === DISPLAY CODE =============================================================
def ms_to_min(ms: int) -> str:
    """
    Converts miliseconds to minutes and seconds.

    Params -
        `ms`: Time in miliseconds

    Returns a `str` with the time in format `MMm SSs`.
    """
    mins = ms // 60000
    sec = (ms % 60000) // 1000
    return f"{mins}m {sec}s"


def reformat_time(time_str: str) -> str:
    """
    Reformats the datetime, purely for aesthetics and nothing else.

    Params -
        `time_str`: The pre-formatted time string.

    Returns a reformatted version of the inputted time.
    """
    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    return dt.strftime("%m-%d-%Y %H:%M")


def display_content(content: List[Dict[str, Any]]) -> None:
    """
    Handles displaying the JSON data into a window, with some slight formatting applied.

    Params -
        `content`: Parsed a validated data from the JSON file.
    """
    for entry in content:
        entry["endTime"] = reformat_time(entry["endTime"])
        entry["msPlayed"] = ms_to_min(entry["msPlayed"])

    root = tk.Tk()
    root.title("Spotify Listening History")
    root.geometry("800x600")

    frame = ttk.Frame(root, padding="3 3 12 12")
    frame.grid(column=0, row=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    columns = list(content[0].keys())
    formatted_columns = ["Time", "Artist", "Track Name", "Time Played"]
    column_widths = [140, 200, 317, 120]

    tree = ttk.Treeview(frame, columns=columns, show="headings", height=28)
    tree.grid(column=0, row=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    for col, formatted_col, width in zip(columns, formatted_columns, column_widths):
        tree.heading(col, text=formatted_col)
        tree.column(col, width=width, anchor=tk.CENTER)

    for entry in content:
        tree.insert("", tk.END, values=[entry[col] for col in columns])

    scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.grid(column=1, row=0, sticky=(tk.N, tk.S))

    root.mainloop()


# === COMPUTE STATISTICS =======================================================
from collections import Counter, defaultdict


def most_played_freq(
    content: List[Dict[str, Any]], top_n: int = 10
) -> List[tuple[str, int]]:
    track_names = [entry["trackName"] for entry in content]
    counter = Counter(track_names)
    return counter.most_common(top_n)


def most_played_by_playtime(content: List[Dict[str, Any]], top_n: int = 10) -> None:
    track_playtimes = defaultdict(int)

    for entry in content:
        track_name = entry["trackName"]
        playtime = entry["msPlayed"]
        track_playtimes[track_name] += playtime

    sorted_tracks = sorted(track_playtimes.items(), key=lambda x: x[1], reverse=True)
    return sorted_tracks[:top_n]


def top_artist_by_playtime(content: List[Dict[str, Any]], top_n: int = 10) -> None:
    artist_playtimes = defaultdict(int)

    for entry in content:
        artist_name = entry["artistName"]
        playtime = entry["msPlayed"]
        artist_playtimes[artist_name] += playtime

    sorted_tracks = sorted(artist_playtimes.items(), key=lambda x: x[1], reverse=True)
    return sorted_tracks[:top_n]


# === MAIN LOGIC CODE ==========================================================
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Display Spotify streaming data.")
    parser.add_argument("file_path", type=str, help="Path to the JSON file with data.")
    args = parser.parse_args()

    init_logger()
    logger.info("Logger intialized.")

    content = get_data(args.file_path)

    if content:
        logger.info("Displaying content to window.")

        top_freq = most_played_freq(content)
        top_playtime = most_played_by_playtime(content)
        top_artist = top_artist_by_playtime(content)

        output_file = "stats.txt"

        logger.info(f"Writing statistics to '{output_file}'.")
        with open(output_file, "w") as file:
            file.write("Top 10 Most Played:\n")
            for index, (track, count) in enumerate(top_freq):
                file.write(f"  {index + 1}. {track} - {count}\n")

            file.write("\nTop 10 Most Played by Playtime:\n")
            for index, (track, time) in enumerate(top_playtime):
                file.write(f"  {index + 1}. {track} - {ms_to_min(time)}\n")

            file.write("\nTop 10 Artist by Playtime:\n")
            for index, (artist, time) in enumerate(top_artist):
                file.write(f"  {index + 1}. {artist} - {ms_to_min(time)}\n")

        display_content(content)

    else:
        logger.info("No content, exiting program...")
        exit(1)


if __name__ == "__main__":
    main()
