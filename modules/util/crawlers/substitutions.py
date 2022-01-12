"""Functionality for scraping the data from lo1.gliwice.pl website to retrieve lesson substitution
details.
"""

# Standard library imports
import json
import re
import datetime

# Third-party imports
import lxml.html

# Local application imports
from .. import web
from ... import Colour, file_manager, util


SUB_INFO_PATTERN = r"(I+)([A-Z]+)([pg]?)(?:(?:\sgr.\s|,\s|\si\s)p. [^,]+?[^-])*\s(.*)"
SUB_INFO_PATTERN = re.compile(SUB_INFO_PATTERN)
SUB_GROUPS_PATTERN = re.compile(r"(?:\sgr.\s|,\s|\si\s)(p. [^,]+?[^-,])\s")

SOURCE_URL = "http://www.lo1.gliwice.pl/zastepstwa-2/"


def get_int_ranges_from_string(lessons_string: str) -> list[int]:
    """Parses a string and returns a list of all integer ranges contained within it.

    For example, the string '1,4-6l' would return the list [1, 4, 5, 6].
    Strings containing no range (e.g. '6l') return a list with the single integer.

    Arguments:
        lessons_string -- the string to parse.
    Returns a list of all the found periods.
    """
    lesson_ints = []
    for lesson in lessons_string.rstrip('l').split(','):
        if "-" in lesson:
            start, end = [int(elem_index) for elem_index in lesson.split('-')]
            lesson_ints += list(range(start, end + 1))
        else:
            lesson_ints.append(int(lesson))
    return lesson_ints


def extract_from_table(elem, table: dict[str, any]) -> None:
    """Parses the table elements."""
    rows = elem[0]
    column_data: list[list[str]] = table["columns"]
    heading_data: list[str] = table["headings"]
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


def extract_actual_substitution(subs_text: str, lesson_dict: dict) -> None:
    """Parses the substitution text elements."""
    separator = " - " if " - " in subs_text else " – "
    lessons, info = subs_text.split(separator, maxsplit=1)
    lesson_ints = get_int_ranges_from_string(lessons)
    for lesson in lesson_ints:
        lesson_dict.setdefault(lesson, {})
        class_year, classes, class_info, details = re.match(SUB_INFO_PATTERN, info).groups()
        for class_letter in classes:
            class_name = f"{class_year}{class_letter}{class_info or ''}"
            lesson_dict[lesson].setdefault(class_name, [])
            class_subs = {
                "details": details,
                "groups": re.findall(SUB_GROUPS_PATTERN, info)
            }
            if not class_subs["groups"]:
                class_subs.pop("groups")
            lesson_dict[lesson][class_name].append(class_subs)


def extract_header_data(elem, elem_index: int, child_elem) -> tuple[str, any]:
    """Parses the main information header elements."""

    if elem.attrib.get("style") == "text-align: center;":
        text = child_elem.xpath("./text()")
        child_elem_text = child_elem.text
        if text:
            child_elem_text = ''.join(text)
        if elem_index == 0:
            date_string = child_elem[0].text.split(' ', maxsplit=1)[1]
            date = datetime.datetime.strptime(date_string, "%d.%m.%Y")
            return "date", str(date.date())
        if elem_index == 1:
            teachers = child_elem_text.split(', ')
            return "teachers", teachers
        return "events", child_elem_text
    if not (child_elem.text and child_elem.text.strip()):
        # Skip blank child elements
        return None, None
    # This is the header for a table
    return "tables", {
        "title": child_elem.text,
        "headings": [],
        "columns": []
    }


def parse_html(html: str) -> dict:
    """Parses the HTML and finds a specific hard-coded substitutions post, then collects the
    relevant data from it.

    Arguments:
        html -- a string containing whole HTML code, e.g. from the contents of a web request's
        response.

    Returns a dictionary containing the extracted data.
    """
    root: lxml.html.Element = lxml.html.fromstring(html)
    post_xpath: str = "//div[@id='content']/div"
    try:
        post_elem: lxml.html.Element = root.xpath(post_xpath)[0]
    except IndexError as no_matches_exc:
        return {"error": util.format_exception_info(no_matches_exc)}
    subs_data = {
        "post": dict(post_elem.attrib),
        "events": [],
        "lessons": {},
        "tables": [],
        "misc": []
    }

    def extract_data(elem: lxml.html.Element, elem_index: int) -> None:
        """Extract the relevant information from each element in the post.

        Adds result to the subs_data dictionary.
        """

        if elem.tag == "table":
            extract_from_table(elem, subs_data["tables"][-1])
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
            if not subs_text or not subs_text.strip():
                # Skip blank 'p' elements
                return
            if "są odwołane" in subs_text:
                subs_data["cancelled"] = subs_text
                return
            try:
                extract_actual_substitution(subs_text, subs_data["lessons"])
            except ValueError:
                # This is not substitutions data
                subs_data["misc"].append(subs_text)
        else:
            # The current element does have children
            if child_elem.tag != "strong":
                return
            key, val = extract_header_data(elem, elem_index, child_elem)
            if not key:
                return
            orig_val = subs_data.get(key)
            if isinstance(orig_val, list):
                orig_val.append(val)
            elif isinstance(orig_val, dict):
                orig_val.update(val)
            else:
                subs_data[key] = val

    for i, p_elem in enumerate(post_elem):
        try:
            # Attempt to extract the relevant data using a hard-coded algorithm
            extract_data(p_elem, i)
        except (LookupError, TypeError, ValueError, AttributeError) as no_matches_exc:
            # Page structure has changed, return the nature of the error.
            subs_data["error"] = util.format_exception_info(no_matches_exc)
            if __name__ == "__main__":
                # Makes the error easier to see for debugging
                print(json.dumps(subs_data, indent=2, ensure_ascii=False))
                raise no_matches_exc from None
            break

    # Return dictionary with substitution data
    return subs_data


def get_substitutions(force_update: bool = False) -> tuple[dict, bool]:
    """Gets the current lesson substitutions. Returns the data itself and a tuple containing a
    boolean indicating if the cache already existed.

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
