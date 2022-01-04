"""Functionality for scraping the data from lo1.gliwice.pl website to retrieve lesson substitution details."""

# Standard library imports
import json
import re
import datetime

# Third-party imports
import lxml.html

# Local application imports
from .. import web
from ... import Colour, file_manager


sub_info_pattern = re.compile(r"(I+)([A-Z]+)([pg]?)(?:(?:\sgr.\s|,\s|\si\s)p. [^,\s]+)*\s(.*)")
sub_groups_pattern = re.compile(r"(?:\sgr.\s|,\s|\si\s)(p. [^,\s]+)")


def parse_html(html: str) -> dict:
    """Parses the HTML and finds a specific hard-coded table, then collects the timetable data from it.

    Arguments:
        html -- a string containing whole HTML code, eg. from the contents of a web request's response.

    Returns a dictionary.
    """
    root: lxml.html.Element = lxml.html.fromstring(html)
    post_xpath: str = "//div[@id='content']/div"
    try:
        post_elem: lxml.html.Element = root.xpath(post_xpath)[0]
    except Exception as e:
        return {"error": type(e).__name__}
    subs_data = {"post": dict(post_elem.attrib), "lessons": {}}
    lesson_list: dict[int, dict[str, list[dict[str, str]]]] = subs_data["lessons"]

    tables = []

    for i, p_elem in enumerate(post_elem):
        if p_elem.tag == "table":
            tables[-1]["rows"] = len(p_elem[0])
            continue
        if p_elem.tag != "p":
            # Skip non-paragraph elements (i.e. comments, divs etc.)
            continue
        if p_elem.text == "&nbsp;":
            # Skip blank 'p' elements
            continue
        try:
            child_elem = p_elem[0]
        except IndexError:
            subs_text: str = p_elem.text
            if subs_text.endswith(" są odwołane."):
                subs_data["ib"] = subs_text
                continue
            separator = " - " if " - " in subs_text else " – "
            lessons, info = subs_text.split(separator, maxsplit=1)
            lesson_ints = []
            for lesson in lessons.rstrip('l').split(','):
                if "-" in lesson:
                    start, end = [int(i) for i in lesson.split('-')]
                    lesson_ints += list(range(start, end + 1))
                else:
                    lesson_ints.append(int(lesson))
            for lesson in lesson_ints:
                info_match = re.match(sub_info_pattern, info)
                groups = re.findall(sub_groups_pattern, info)
                class_year, classes, class_info, details = info_match.groups()
                lesson_list.setdefault(lesson, {})
                for class_letter in classes:
                    class_name = f"{class_year}{class_letter}{class_info or ''}"
                    lesson_list[lesson].setdefault(class_name, [])
                    substitution_info = {}
                    if groups:
                        substitution_info["groups"] = groups
                    substitution_info["details"] = details
                    lesson_list[lesson][class_name].append(substitution_info)
        else:
            if child_elem.tag == "strong":
                if i == 0:
                    date_string = child_elem[0].text.split(' ', maxsplit=1)[1]
                    date = datetime.datetime.strptime(date_string, "%d.%m.%Y").date()
                    subs_data["date"] = str(date)
                    continue
                if i == 1:
                    teachers = child_elem.text.split(', ')
                    subs_data["teachers"] = teachers
                    continue
                if i == 2:
                    subs_data["misc"] = child_elem.text
                    continue
                if not (child_elem.text and child_elem.text.strip()):
                    # Skip blank child elements
                    print(f"Skipping element {i}: only whitespace child")
                    continue
                tables.append({"heading": child_elem.text})
                continue

    # Sort the lesson substitutions by period number in ascending order
    # subs_data["lessons"] = {l: sorted(subs) for l, subs in sorted(lesson_list.items())}

    # Add the list of tables to the data
    subs_data["tables"] = tables

    # Return dictionary with substitution data
    return subs_data


def get_substitutions(force_update: bool = False) -> tuple[dict, bool]:
    """Gets the current lesson substitutions.
    Returns the data itself and a tuple containing a boolean indicating if the cache already existed.

    Arguments:
        force_update -- a boolean indicating if the cache should be forcefully updated.
    """
    update_cache_callback: function = lambda force: parse_html(
        web.get_html("http://www.lo1.gliwice.pl/zastepstwa-2/", force))
    return file_manager.get_cache("subs", force_update, update_cache_callback)


if __name__ == "__main__":
    colours = vars(Colour)
    for col in colours:
        if not col.startswith('_') and col is not None:
            print(f"Colour {colours[col]}{col}{Colour.ENDC}")
    print()
    try:
        plan = json.dumps(get_substitutions(
            True)[0], indent=4, ensure_ascii=False)
        print(f"{Colour.OKGREEN}Substitutions:\n{Colour.ENDC}{plan}")
    except KeyboardInterrupt:
        print(f"...{Colour.FAIL}\nGoodbye!\n{Colour.ENDC}")
