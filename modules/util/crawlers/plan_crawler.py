"""Functionality for scraping the data from lo1.gliwice.pl website to retrieve lesson plan details."""
import json
import os
import re

# If this script is run manually, it must be done so from a root package with the -m flag. For example:
# ... dzwonnik-2/modules $ python -m util.crawlers.plan_crawler
from .. import web_api
from ... import file_management

period_pattern = re.compile(r"^<td class=\"nr\">(\d\d?)</td>$")
duration_pattern = re.compile(r"^<td class=\"g\">\s?(\d\d?):(\d\d)-\s?(\d\d?):(\d\d)</td>$")
pattern = re.compile(r"<span class=\"p\">([^#]+?)(?:-(\d+)/(\d+))?</span>.*?(?:<a .*?class=\"n\">(.+?)</a>"
                     r"|<span class=\"p\">(#.+?)</span>) <a .*?class=\"s\">(.+?)</a>")

# Tags that should not increment or decrement a line's tag depth
ignored_tags = ["hr", "br"]

class colour:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def get_plan_id(class_id: str or int = None) -> int:
    """Gets the plan ID that is used on the school website of a given class.
    
    Arguments:
        class_id -- a string representing the name of the class, or an integer representing the lesson plan ID.
    """

    if type(class_id) is int and 1 <= class_id <= 16:
        return class_id
    class_id = "2d" if class_id is None else class_id
    try:
        class_year = int(class_id[0])
        class_letter = class_id[1]
        if not 1 <= class_year <= 3:
            raise ValueError
        # 3 is the number of classes in year 3 that are type "g" (gimnazjum)
        # 6 and 5 are the numbers of classes in year 3 and 2, respectively
        # noinspection SpellCheckingInspection
        base_id = "abcde".index(class_letter.lower()) + 1
        return base_id + ((3 * (class_id[2].lower() == "p")) if class_year == 3 else (6 + 5 * (class_year == 1)))
    except (ValueError, IndexError):
        raise ValueError(f"Invalid class name: {class_id}.")


def get_plan_link(class_id: str or int) -> str:
    """Gets the link to a given class' lesson plan.

    Arguments:
        class_id -- a string representing the name of the class, or an integer representing the lesson plan ID.
    """
    return f"http://www.lo1.gliwice.pl/wp-content/uploads/static/plan/plany/o{get_plan_id(class_id)}.html"


def parse_html(html: str) -> dict[str, list[list[dict[str, str]]]]:
    """Parses the HTML and finds a specific hard-coded table, then collects the timetable data from it.

    Arguments:
        html -- a string containing whole HTML code, eg. from the contents of a web request's response.

    Returns a dictionary that assigns a list of lessons (lesson, group, room_id, [teacher]) to each weekday name.
    """
    tag_index = seen_tables = row_number = column_number = 0
    headers = []
    data: dict[str, list[list[dict[str, str]]]] = {}

    def extract_regex() -> any:
        """Extracts the data from a given table row."""

        if row == "<td class=\"l\">&nbsp;</td>":
            return []
        elif row.startswith("<td class=\"nr\">"):
            # Row containing the lesson period number
            return int(period_pattern.match(row).groups()[-1])
        elif row.startswith("<td class=\"g\">"):
            # Row containing the lesson period start hour, start minute, end hour and end minute
            # eg. [8, 0, 8, 45] corresponds to the lesson during 08:00 - 08:45
            times = [int(time) for time in duration_pattern.match(row).groups()]
            return [times[:2], times[2:]]
        else:
            # Row containing lesson information for a given period
            tmp: list[dict[str, str]] = []
            for match in pattern.findall(row):
                lesson_name, group, groups, teacher, code, room_id = match
                if group: 
                    if int(groups) == 5:
                        group = ["RB", "RCH", "RH", "RG", "RF"][int(group) - 1]
                else:
                    # If the group is not specified but the room code is, use that instead
                    # If neither are, check if the current lesson is Religious Studies (and set the group accordingly)
                    # Finally, if none of the above, set the group to 'grupa_0' (whole class)
                    group = code.lstrip('#') if code else 'rel' if lesson_name == "religia" else '0'
                name = lesson_name.replace("r_j.", "j.").replace(" DW", "").replace("j. ", "j.").replace('r_', 'r-')
                tmp.append({
                    # Replace extended language lessons with the regular variant since there is no practical distinction
                    "name": name.replace(' ', '-'),
                    "group": "grupa_" + group,
                    "room_id": room_id
                })
                if teacher:
                    # Add the teacher to the returned lesson info if they are specified in the given data
                    tmp[-1]["teacher"] = teacher
            return tmp

    # Go through each line in the inputted HTML
    for row in html.splitlines():
        # Increment the tag depth if the line introduces a new tag
        # Decremenet the tag depth if the line contains a closing tag
        # Ignore tags like '<hr>', '<br>' that are defined above
        tag_index += row.count("<") - 2 * row.count("</") - sum([row.count(f"<{tag}>") for tag in ignored_tags])
        if "<table" in row:
            # Increment the number of tables that have been met so far
            seen_tables += row.count('<table')
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
                data[weekday].append(extract_regex())
    #             print(f"{colour.OKCYAN}row {row_number}{colour.ENDC}, seen {colour.OKGREEN}{seen_tables} tables {colour.WARNING}| {row}")
    # print(colour.ENDC)
    return data


def get_lesson_plan(class_id: str or int, force_update = False) -> dict[str, list[list[dict[str, str]]]]:
    """Gets the lesson plan for a given class.

    Arguments:
        class_id -- a string representing the name of the class, or an integer representing the lesson plan ID.
        force_update -- a boolean indicating if the cache should be forcefully updated.
    """
    plan_id = get_plan_id(class_id)
    update_cache_callback: function = lambda: parse_html(web_api.get_html(get_plan_link(plan_id), force_update))
    return file_management.get_cache(f"plan_{plan_id}", update_cache_callback)

if __name__ == "__main__":
    colours = vars(colour)
    for col in colours:
        if not col.startswith('_') and col is not None:
            print(f"Colour {colours[col]}{col}{colour.ENDC}")
    print()
    input_msg = f"{colour.OKBLUE}Enter {colour.OKGREEN}{colour.UNDERLINE}class name{colour.ENDC}{colour.OKBLUE}...\n{colour.WARNING}> "
    try:
        while True:
            plan = json.dumps(get_lesson_plan(input(input_msg), force_update=True), indent=4, ensure_ascii=False)
            print(f"{colour.OKGREEN}Lesson plan:\n{colour.ENDC}{plan}")
    except KeyboardInterrupt:
        print(f"...{colour.FAIL}\nGoodbye!\n{colour.ENDC}")
