"""Functionality for parsing the data from lo1.gliwice.pl to retrieve lesson plan details."""

# Standard library imports
import json
import re

# Third-party imports
from corny_commons import file_manager
from corny_commons.util import web

# Local application imports
from modules import Colour
from modules.util import OUR_CLASS

PERIOD_PATTERN = re.compile(r"^<td class=\"nr\">(\d\d?)</td>$")
DURATION_PATTERN = r"^<td class=\"g\">\s?(\d\d?):(\d\d)-\s?(\d\d?):(\d\d)</td>$"
DURATION_PATTERN = re.compile(DURATION_PATTERN)
LESSON_PATTERN = (
    r"<span class=\"p\">([^#]+?)(?:-(\d+)/(\d+))?</span>.*?(?:<a .*?class=\"n\">"
    r"(.+?)</a>|<span class=\"p\">(#.+?)</span>) <a .*?class=\"s\">(.+?)</a>"
)
LESSON_PATTERN = re.compile(LESSON_PATTERN)

# Tags that should not increment or decrement a line's tag depth
IGNORED_TAGS = ["hr", "br"]
SOURCE_URL = "http://www.lo1.gliwice.pl/wp-content/uploads/static/plan/plany/o{id}.html"

# Until the end of school year 2022-2023, classes ABC are non-IB and classes DE are IB.
# Change this in sept 2023 when there are 4 non-IB classes and classes EF are IB.
CLASSES_PER_YEAR = {4: 3, 3: 3, 2: 5, 1: 6}
NUM_IB_CLASSES_PER_YEAR = 2
IB_FIRST_YEAR = 3

SUBJECT_NAME_MAPPINGS = {
    "mat": "r-mat",
    "mat.": "mat",
    "matematyka": "mat",
    "chem.": "chemia",
    "fiz.": "fizyka",
}


def get_plan_id(input_id: str or int = None) -> int:
    """Gets the plan ID that is used on the school website of a given class.

    Arguments:
        class_id -- a string representing the name of the class,
        or an integer representing the lesson plan ID.
    """

    # LESSON PLANS:
    # o1 -- 4ap
    # o2 -- 4bp
    # o3 -- 4cp

    # o4 -- 3a
    # o5 -- 3b
    # o6 -- 3c

    #  o7 -- 2a
    #  o8 -- 2b
    #  o9 -- 2c
    # o10 -- 2d
    # o11 -- 2e

    # o12 -- 1a
    # o13 -- 1b
    # o14 -- 1c
    # o15 -- 1d
    # o16 -- 1e
    # o17 -- 1f

    # If the input is already an integer, validate it
    if isinstance(input_id, int):
        if not 1 <= input_id <= 17:
            raise ValueError(f"Invalid integer plan ID: {input_id}.") from None
        return input_id

    input_id = OUR_CLASS if input_id is None else input_id
    try:
        class_year = int(input_id[0])
    except (ValueError, IndexError) as raw_exc:
        raise ValueError(f"'{input_id}' does not start with a number.") from raw_exc
    num_classes_this_year = CLASSES_PER_YEAR.get(class_year)
    if num_classes_this_year is None:
        raise ValueError(f"Year {class_year} is an invalid class year.")
    try:
        class_letter = input_id[1].lower()
    except IndexError as raw_exc:
        raise ValueError(
            f"Missing class letter in class name '{input_id}'."
        ) from raw_exc
    class_letters = [chr(letter + ord("a")) for letter in range(num_classes_this_year)]

    try:
        class_id = class_letters.index(class_letter) + 1
    except ValueError as raw_exc:
        msg = f"Invalid class letter: there is no class '{class_letter}' in year {class_year}."
        raise ValueError(msg) from raw_exc

    # This is not an IB class
    for year in range(4, class_year, -1):
        # Add the number of classes each year before the current class
        class_id += CLASSES_PER_YEAR[year]

    # Recursive call to validate the plan ID integer
    return get_plan_id(class_id)


def get_plan_link(class_id: str or int) -> str:
    """Gets the link to a given class' lesson plan.

    Arguments:
        class_id -- a string representing the name of the class,
        or an integer representing the lesson plan ID.
    """
    return SOURCE_URL.format(id=get_plan_id(class_id))


def parse_html(html: str) -> dict[str, list[list[dict[str, str]]]]:
    """Parses the HTML and finds a specific table, then collects the timetable data from it.

    Arguments:
        html -- a string containing whole HTML code, e.g. from the contents of a web response.

    Returns a dictionary that assigns a list of lessons (lesson, group, room_id, [teacher])
    to each weekday name.
    """
    tag_index = seen_tables = row_number = column_number = 0
    headers = []
    data: dict[str, list[list[dict[str, str]]]] = {}

    def extract_regex(raw_line: str) -> any:
        """Extracts the data from a given table row."""

        # Return an empty list if the current cell is empty
        if raw_line == '<td class="l">&nbsp;</td>':
            return []
        if raw_line.startswith('<td class="nr">'):
            # Row containing the lesson period number
            return int(PERIOD_PATTERN.match(raw_line).groups()[-1])
        if raw_line.startswith('<td class="g">'):
            # Row containing the lesson period start hour, start minute, end hour and end minute
            # e.g. [8, 0, 8, 45] corresponds to the lesson during 08:00 - 08:45
            times = tuple(
                int(time) for time in DURATION_PATTERN.match(raw_line).groups()
            )
            # Check if the lesson start hour is less than 12:00 (i.e. old timetable still relevant)
            lesson_start_hour = times[0]
            if lesson_start_hour < 12:
                return times[:2], times[2:]
            # The lesson is after or 12:00.
            # We must manually change the returned values since the timetable is not up-to-date.
            # After 12:00, the breaks last 5 minutes instead of 10.
            new_times = {
                12: ((12, 50), (13, 35)),
                13: ((13, 40), (14, 25)),
                14: ((14, 30), (15, 15)),
                15: ((15, 20), (16, 5)),
            }
            return new_times[lesson_start_hour]
        # Row containing lesson information for a given period
        tmp: list[dict[str, str]] = []
        for match in LESSON_PATTERN.findall(raw_line):
            lesson_name, group, groups, teacher, code, room_id = match
            if group:
                if int(groups) == 5:
                    group = ["RB", "RCH", "RH", "RG", "RF"][int(group) - 1]
            else:
                # Group is not specified in timetable
                if code:
                    # If the room code is specified, use that instead.
                    group = code.lstrip("#")
                elif lesson_name == "religia":
                    # If the current lesson is Religious Studies, use that code.
                    group = "rel"
                else:
                    # Set group to 'grupa_0' (whole class).
                    group = "0"
            mappings = (
                ("r_j.", "j."),  # Remove the "r_" prefix for extended language classes
                (
                    " DW",
                    "",
                ),  # Remove "DW" (stands for "dwujęzyczne"; taught in two languages)
                ("j. ", "j."),  # Remove trailing spaces
                (
                    "r_",
                    "r-",
                ),  # Replace '_' with '-' to improve Discord markdown formatting
                (" ", "-"),  # Replace whitespaces with hyphens so the code is one word
            )
            name: str = lesson_name
            for mapping in mappings:
                name = name.replace(*mapping)
            # Edge case mappings
            name = SUBJECT_NAME_MAPPINGS.get(name, name)
            tmp.append(
                {"name": name.lower(), "group": "grupa_" + group, "room_id": room_id}
            )
            if teacher:
                # Add the teacher to the returned lesson info if they are specified
                tmp[-1]["teacher"] = teacher
        return tmp

    # Go through each line in the inputted HTML
    for row in html.splitlines():
        # Increment the tag depth if the line introduces a new tag
        # Decremenet the tag depth if the line contains a closing tag
        # Ignore tags like '<hr>', '<br>' that are defined above
        tag_index += (
            row.count("<")
            - 2 * row.count("</")
            - sum([row.count(f"<{tag}>") for tag in IGNORED_TAGS])
        )
        if "<table" in row:
            # Increment the number of tables that have been met so far
            seen_tables += row.count("<table")
        # The table containing the lesson plans is the 3rd table
        if seen_tables == 3:
            if row == "<tr>":
                row_number += 1
                column_number = 0
                continue
            if row_number == 1 and row.startswith("<th>"):
                headers.append(row.lstrip("<th>").rstrip("</th>"))
            elif row.startswith("<td"):
                weekday = headers[column_number]
                column_number += 1
                if weekday not in data:
                    data[weekday] = []
                data[weekday].append(extract_regex(row))
    # Report summary of scraped data
    # for key in data:
    #     _log(f"{key}: {len(data[key])}")
    #     if key in ["Nr", "Godz"]:
    #         continue
    #     for period, lessons in enumerate(data[key]):
    #         _log(f"    period {period}: {len(lessons)} lesson(s)")

    # Add a timetable entry that is not present in the online lesson plan
    if "Godz" in data and isinstance(data["Godz"], list):
        # Lesson period 10 from 16:10 - 16:55
        data["Godz"].append([[16, 10], [16, 55]])
    return data


def get_lesson_plan(
    class_id=OUR_CLASS, force_update: bool or None = False
) -> tuple[dict, bool]:
    """Gets the lesson plan for a given class. Returns a tuple containing the data itself
    and a boolean indicating if the cache already existed.

    Arguments:
        `class_id` -- the lesson plan ID integer, or a string representing the name of the class.

        `force_update` -- a boolean indicating if the cache should be forcefully updated.
        Can also be set to `None`, which doesn't update the cache if it exists, but ignores the
        web request limit if it doesn't.
    """
    plan_id = get_plan_id(class_id)

    def update_cache_callback() -> dict:
        ignore_limit: bool = force_update or force_update is None
        plan_link: str = get_plan_link(plan_id)
        html: str = web.get_html(plan_link, ignore_request_limit=ignore_limit)
        return parse_html(html)

    log_msg = f"Getting lesson plan with ID {plan_id} for class '{class_id}' ({force_update=}) ..."
    _log(log_msg)
    return file_manager.get_cache(
        f"plan_{plan_id}", force_update, update_cache_callback
    )


def get_lesson_plan_dp():
    """Reads the lesson plan for the DP class."""
    with open("plan-dp1.json", "r", encoding="utf-8") as file:
        lesson_plan: list[list[dict]] = json.load(file)
    random_plan, _ = get_lesson_plan(1)
    return {"times": random_plan["Godz"], "weekdays": lesson_plan}


def _log(*args):
    if __name__ == "__main__":
        print(*args)
        return
    file_manager.log(*args, filename="bot")


if __name__ == "__main__":
    colours = vars(Colour)
    for col in colours:
        if not col.startswith("_") and col is not None:
            _log(f"Colour {colours[col]}{col}{Colour.ENDC}")
    _log()
    input_msg = (
        f"{Colour.OKBLUE}Enter {Colour.OKGREEN}{Colour.UNDERLINE}class name{Colour.ENDC}"
        f"{Colour.OKBLUE}...\n{Colour.WARNING}> "
    )
    try:
        while True:
            try:
                raw_data = get_lesson_plan(input(input_msg), force_update=True)[0]
            except ValueError as err:
                print(f"{Colour.FAIL}Error: {err}")
                continue
            plan = json.dumps(raw_data, indent=2, ensure_ascii=False)
            print(Colour.ENDC)
            _log(f"{Colour.OKGREEN}Lesson plan:\n{Colour.ENDC}{list(raw_data.keys())}")
    except KeyboardInterrupt:
        _log(f"...{Colour.FAIL}\nGoodbye!\n{Colour.ENDC}")
