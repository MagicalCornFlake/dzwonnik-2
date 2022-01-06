"""Functionality for scraping the data from lo1.gliwice.pl website to retrieve lesson substitution details."""

# Standard library imports
import json
import re
import datetime

# Third-party imports
import lxml.html

# Local application imports
from .. import web
from ... import Colour, file_manager, util


sub_info_pattern = re.compile(
    r"(I+)([A-Z]+)([pg]?)(?:(?:\sgr.\s|,\s|\si\s)p. [^,\s]+)*\s(.*)")
sub_groups_pattern = re.compile(r"(?:\sgr.\s|,\s|\si\s)(p. [^,\s]+)")

SOURCE_URL = "http://www.lo1.gliwice.pl/zastepstwa-2/"


def parse_html(html: str) -> dict:
    """Parses the HTML and finds a specific hard-coded substitutions post, then collects the relevant data from it.

    Arguments:
        html -- a string containing whole HTML code, e.g. from the contents of a web request's response.

    Returns a dictionary.
    """
    root: lxml.html.Element = lxml.html.fromstring(html)
    post_xpath: str = "//div[@id='content']/div"
    try:
        post_elem: lxml.html.Element = root.xpath(post_xpath)[0]
    except Exception as e:
        return {"error": util.format_exception_info(e)}
    subs_data = {"post": dict(post_elem.attrib), "events": [], "lessons": {}}
    lesson_list: dict[int, dict[str, list]] = subs_data["lessons"]

    tables = []

    def extract_data(elem: lxml.html.Element, elem_index: int):
        """Extract the relevant information from each element in the post. Adds result to the subs_data dictionary."""
        if elem.tag == "table":
            rows = elem[0]
            table_data: dict[str, any] = tables[-1]
            column_data: list[list[str]] = table_data["columns"]
            heading_data: list[str] = table_data["headings"]
            for i, row in enumerate(rows):
                for j, cell in enumerate(row):
                    try:
                        cell_text = cell[0].text
                    except IndexError:
                        cell_text = cell.text
                    if i == 0:
                        # Add the header of the column
                        heading_data.append(cell_text)
                        # Add empty list to hold the rows of that column
                        column_data.append([])
                        continue
                    column_data[j].append(cell_text)
            return
        if elem.tag != "p":
            # Skip non-paragraph elements (i.e. comments, divs etc.)
            return
        try:
            # Check if this element has children
            child_elem = elem[0]
        except IndexError:
            # The current element has no children
            subs_text: str = elem.text
            if not (subs_text and subs_text.strip()):
                # Skip blank 'p' elements
                return
            if "są odwołane" in subs_text:
                subs_data["cancelled"] = subs_text
                return
            separator = " - " if " - " in subs_text else " – "
            lessons, info = subs_text.split(separator, maxsplit=1)
            lesson_ints = []
            for lesson in lessons.rstrip('l').split(','):
                if "-" in lesson:
                    start, end = [int(elem_index)
                                  for elem_index in lesson.split('-')]
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
            # The current element does have children
            if child_elem.tag != "strong":
                return
            if elem.attrib.get("style") == "text-align: center;":
                text = child_elem.xpath(f"./text()")
                child_elem_text = child_elem.text
                if text:
                    child_elem_text = ''.join(text)
                if elem_index == 0:
                    date_string = child_elem[0].text.split(' ', maxsplit=1)[1]
                    date = datetime.datetime.strptime(date_string, "%d.%m.%Y")
                    subs_data["date"] = str(date.date())
                    return
                if elem_index == 1:
                    teachers = child_elem_text.split(', ')
                    subs_data["teachers"] = teachers
                    return
                subs_data["events"].append(child_elem_text)
                return
            if not (child_elem.text and child_elem.text.strip()):
                # Skip blank child elements
                return
            tables.append({
                "title": child_elem.text,
                "headings": [],
                "columns": []
            })

    for i, p_elem in enumerate(post_elem):
        try:
            # Attempt to extract the relevant data using a hard-coded algorithm
            extract_data(p_elem, i)
        except Exception as e:
            # Page structure has changed, return the nature of the error.
            subs_data["error"] = util.format_exception_info(e)
            if __name__ == "__main__":
                # Makes the error easier to see for debugging
                raise e from None
            break

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
    def update_cache_callback() -> dict:
        html: str = web.get_html(SOURCE_URL, force_update)
        return parse_html(html)
    return file_manager.get_cache("subs", force_update, update_cache_callback)


if __name__ == "__main__":
    colours = vars(Colour)
    for col in colours:
        if not col.startswith('_') and col is not None:
            print(f"Colour {colours[col]}{col}{Colour.ENDC}")
    print()
    try:
        subs: dict = get_substitutions(force_update=True)[0]
        plan = json.dumps(subs, indent=2, ensure_ascii=False)
        print(f"{Colour.OKGREEN}Substitutions:\n{Colour.ENDC}{plan}")
    except KeyboardInterrupt:
        print(f"...{Colour.FAIL}\nGoodbye!\n{Colour.ENDC}")
