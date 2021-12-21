"""Functionality for scraping the data from lo1.gliwice.pl website to retrieve lesson plan details"""
import importlib
import re

if __name__ == "__main__":
    from ..api import web_api
else:
    web_api = importlib.import_module('modules.util.api.web_api')

period_pattern = re.compile(r"^<td class=\"nr\">(\d\d?)</td>$")
duration_pattern = re.compile(r"^<td class=\"g\">\s?(\d\d?):(\d\d)-\s?(\d\d?):(\d\d)</td>$")
pattern = re.compile(r"<span class=\"p\">([^#]+?)(?:-(\d+)/(\d+))?</span>.*?(?:<a .*?class=\"n\">(.+?)</a>|"
                     r"<span class=\"p\">(#.+?)</span>) <a .*?class=\"s\">(.+?)</a>")


def get_plan_id(class_name: str or int = None) -> int:
    """Gets the plan ID that is used on the school website of a given class."""
    if type(class_name) is int and 1 <= class_name <= 16:
        return class_name
    class_name = "2d" if class_name is None else class_name
    try:
        class_year = int(class_name[0])
        class_letter = class_name[1]
        if not 1 <= class_year <= 3:
            raise ValueError
        # 3 is the number of classes in year 3 that are type "g" (gimnazjum)
        # 6 and 5 are the numbers of classes in year 3 and 2, respectively
        # noinspection SpellCheckingInspection
        base_id = "abcde".index(class_letter.lower()) + 1
        return base_id + ((3 * (class_name[2].lower() == "p")) if class_year == 3 else (6 + 5 * (class_year == 1)))
    except (ValueError, IndexError):
        raise ValueError(f"Invalid class name: {class_name}.")


def get_plan_link(class_id: str or int) -> str:
    """Gets the link to a given class' lesson plan.

    Arguments:
        class_id -- can be a string representing the class name or an integer representing the lesson plan ID.
    """
    return f"http://www.lo1.gliwice.pl/wp-content/uploads/static/plan/plany/o{get_plan_id(class_id)}.html"


def parse_html(html: str) -> dict[str, list[list[dict[str, str]]]]:
    """Parses the HTML and finds a specific hard-coded table, then collects the timetable data from it.

    Arguments:
        html -- a string containing whole HTML code, eg. from the contents of a web request's response.

    Returns a dictionary that assigns a list of lessons (lesson, group, room_id, [teacher]) to each weekday name.
    """
    table_tag_index = tag_index = seen_tables = row_number = column_number = 0
    headers = []
    data: dict[str, list[list[dict[str, str]]]] = {}

    def extract_regex() -> str or list[str]:
        if row == "<td class=\"l\">&nbsp;</td>":
            return "---"
        elif row.startswith("<td class=\"nr\">"):
            return period_pattern.match(row).groups()[-1]
        elif row.startswith("<td class=\"g\">"):
            return [int(time) for time in duration_pattern.match(row).groups()]
        else:
            tmp: list[dict[str, str]] = []
            for match in pattern.findall(row):
                lesson, group, groups, teacher, code, room_id = match
                if group and int(groups) == 5:
                    group = ["RB", "RCH", "RH", "RG", "RF"][int(group) - 1]
                else:
                    group = code.lstrip('#') if code else 'rel' if lesson == "religia" else '0'
                tmp.append({
                    "lesson": lesson.replace("r_j.", "j."),
                    "group": "grupa_" + group,
                    "room_id": room_id
                })
                if teacher:
                    tmp[-1]["teacher"] = teacher
            return tmp

    for row in html.splitlines():
        tag_index += row.count("<") - 2 * row.count("</") - row.count("<br>") - row.count("<hr>")
        if "<table" in row:
            table_tag_index += 1
            seen_tables += 1
        if seen_tables == 3 and table_tag_index == 2:
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
                # print("row", row_number, "|", row)
        if "</table>" in row:
            table_tag_index -= 1
    for row in data:
        print(row)
        for column in data[row]:
            print(column)
    return data


def get_lesson_plan(class_id: str) -> dict[str, list[list[dict[str, str]]]]:
    """Gets the lesson plan for a given class.

    Arguments:
        class_id -- a string representing the name of the class.
    """
    link = get_plan_link(get_plan_id(class_id))
    html = web_api.make_request(link).content.decode('UTF-8')
    return parse_html(html)
