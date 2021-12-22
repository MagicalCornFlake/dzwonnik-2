"""Functionality for scraping the data from lo1.gliwice.pl website to retrieve lesson plan details."""
import json
import re
import lxml.html

# If this script is run manually, it must be done so from a root package with the -m flag. For example:
# ... dzwonnik-2/modules $ python -m util.crawlers.plan_crawler
from .. import web_api
from ... import file_management
from ... constants import Colour

duration_pattern = re.compile(r"\s?(\d\d?):(\d\d)-\s?(\d\d?):(\d\d)")
lesson_pattern = re.compile(r"<span class=\"p\">([^#]+?)(?:-(\d+)/(\d+))?</span>.*?(?:<a .*?class=\"n\">(.+?)</a>"
                            r"|<span class=\"p\">(#.+?)</span>) <a .*?class=\"s\">(.+?)</a>")

# Tags that should not increment or decrement a line's tag depth
ignored_tags = ["hr", "br"]


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

    def extract_regex(elem: lxml.html.Element) -> any:
        """Extracts the data from a given table row."""

        if elem.attrib["class"] == "nr":
            # Row containing the lesson period number
            return int(elem.text)
        elif elem.attrib["class"] == "g":
            # Row containing the lesson period start hour, start minute, end hour and end minute
            # eg. [8, 0, 8, 45] corresponds to the lesson during 08:00 - 08:45
            times = [int(time) for time in duration_pattern.search(elem.text).groups()]
            return [times[:2], times[2:]]
        else:
            elem_str = lxml.html.tostring(elem).decode('UTF-8')
            # Row containing lesson information for a given period
            
            tmp: list[dict[str, str]] = []
            for match in lesson_pattern.findall(elem_str):
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

    data: dict[str, list[list[dict[str, str]]]] = {}
    headers = []
    root = lxml.html.fromstring(html)
    table_element = root.xpath("//html/body/div/table/tr/td/table")[0]
    for table_row in table_element:
        for i, column in enumerate(table_row):
            if column.tag == "th":
                headers.append(column.text)
            elif column.tag == "td":
                weekday = headers[i]
                if weekday not in data:
                    data[weekday] = []
                data[weekday].append(extract_regex(column))
    return data


def get_lesson_plan(class_id: str or int = "2d", force_update = False) -> tuple[dict, bool]:
    """Gets the lesson plan for a given class.
    Returns the data itself and a tuple containing a boolean indicating if the cache already existed.

    Arguments:
        class_id -- a string representing the name of the class, or an integer representing the lesson plan ID.
        force_update -- a boolean indicating if the cache should be forcefully updated.
    """
    plan_id = get_plan_id(class_id)
    update_cache_callback: function = lambda force: parse_html(web_api.get_html(get_plan_link(plan_id), force))
    return file_management.get_cache(f"plan_{plan_id}", force_update, update_cache_callback)


if __name__ == "__main__":
    colours = vars(Colour)
    for col in colours:
        if not col.startswith('_') and col is not None:
            print(f"Colour {colours[col]}{col}{Colour.ENDC}")
    print()
    input_msg = f"{Colour.OKBLUE}Enter {Colour.OKGREEN}{Colour.UNDERLINE}class name{Colour.ENDC}{Colour.OKBLUE}...\n{Colour.WARNING}> "
    try:
        while True:
            plan = json.dumps(get_lesson_plan(input(input_msg), force_update=True)[0], indent=4, ensure_ascii=False)
            print(f"{Colour.OKGREEN}Lesson plan:\n{Colour.ENDC}{plan}")
    except KeyboardInterrupt:
        print(f"...{Colour.FAIL}\nGoodbye!\n{Colour.ENDC}")
