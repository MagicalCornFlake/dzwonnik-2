"""Functionality for scraping the data from lo1.gliwice.pl website to retrieve lesson substitution
details.
"""

# Standard library imports
import json
import re
import datetime
from sqlite3 import IntegrityError

# Third-party imports
import lxml.html
from corny_commons import file_manager, util as ccutil
from corny_commons.util import web

# Local application imports
from modules import WEEKDAY_NAMES, Colour, util
from modules.api.lesson_plan import get_lesson_plan


SUB_INFO_PATTERN = r"(I*)([A-Z]*)([pg]?)\s?(?:(?:gr.\s|,\s|\si\s)p. [^,]+?[^-])*\s(.*)"
SUB_INFO_PATTERN = re.compile(SUB_INFO_PATTERN)
SUB_GROUPS_PATTERN = re.compile(r"\s?(?:gr.\s|,\s|\si\s)(p. [^,]+?[^-,])\s")

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
    lesson_hours = lessons_string.rstrip("l")
    lesson_hours = lesson_hours.split("i" if "i" in lesson_hours else ",")
    for lesson in lesson_hours:
        if "-" in lesson:
            start, end = lesson.split('-')
            lesson_ints += range(int(start), int(end) + 1)
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


def get_substituted_lessons(class_name: str, weekday: int, period: IntegrityError):
    """Checks the lesson plan for the lessons that would normally have taken place."""
    class_id: str = util.format_class(class_name, reverse=True)
    try:
        lesson_plan: dict[str, list[list[dict]]] = get_lesson_plan(class_id, force_update=None)[0]
    except ValueError:
        # The class has no lesson plan
        lessons_on_period: list[dict] = []
    else:
        weekday_name = WEEKDAY_NAMES[weekday]
        lessons_on_period: list[dict] = lesson_plan[weekday_name][period]
    return lessons_on_period


def extract_substitutions_text(elem_text: str, subs_data: dict) -> None:
    """Parses the substitution text elements."""
    # Check which dash symbol is used in the substitutions text
    # Usually it's the EN dash, although it's possible it's the minus symbol
    # Yes, this is supposed to be U+2013
    separator = " - " if " - " in elem_text else " – "
    try:
        lessons, info = elem_text.split(separator, maxsplit=1)
    except ValueError:
        # This is not substitutions data
        subs_data["misc"].append(elem_text)
        return
    lesson_ints = get_int_ranges_from_string(lessons)
    if "date" in subs_data:
        # Parse the date from the substitutions page
        weekday_int: int = datetime.datetime.strptime(
            subs_data["date"], "%Y-%m-%d").weekday()
    else:
        # Default to Monday; this shouldn't be possible
        # The date is usually the first element in the page contents
        # This would mean that for some reason it's not included on the substitutions page
        # (which hasn't happened yet)
        file_manager.log(
            "No date provided in substitutions data. Defaulting to Monday.")
        weekday_int: int = 0

    match = SUB_INFO_PATTERN.match(info)
    if match is None:
        file_manager.log("Could not find a lesson entry match for", info)
        return
    class_year, classes, class_info, details = match.groups()

    for lesson in lesson_ints:
        subs_data["lessons"].setdefault(lesson, {})
        for class_letter in classes or "?":
            class_name = f"{class_year or ''}{class_letter}{class_info or ''}"
            subs_data["lessons"][lesson].setdefault(class_name, {
                "substituted_lessons": get_substituted_lessons(class_name, weekday_int, lesson),
                "substitutions": []
            })
            class_subs = {
                "details": details,
                "groups": SUB_GROUPS_PATTERN.findall(info)
            }
            if not class_subs["groups"]:
                class_subs.pop("groups")
            subs_data["lessons"][lesson][class_name]["substitutions"].append(
                class_subs)


def extract_header_data(elem, child_elems, subs_data) -> tuple[str, any]:
    """Parses the main information header elements."""
    child_elem_text = "".join([chld.text or "" for chld in child_elems])
    if "text-align: center;" not in elem.attrib.get("style", ""):
        # This is not an informational header
        if not (child_elem_text and child_elem_text.strip()):
            # Skip blank child elements
            return
        # This is the header for a table
        subs_data["tables"].append({
            "title": child_elem_text,
            "headings": [],
            "columns": []
        })
        return
    try:
        # Check if the child element has an 'underline' child element with the date text
        date_string = child_elems[0][0].text.lstrip("Zastępstwa ")
        date = datetime.datetime.strptime(date_string, "%d.%m.%Y")
    except (IndexError, ValueError):
        if child_elem_text.upper() == child_elem_text:
            # The text is all uppercase.
            subs_data["misc"].append(child_elem_text)
            return
        if "teachers" in subs_data:
            subs_data["events"].append(child_elem_text)
            return
        subs_data["teachers"] = child_elem_text.split(', ')
    else:
        # This is the element header containing the substitutions date
        subs_data["date"] = str(date.date())


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
        return {"error": ccutil.format_exception_info(no_matches_exc)}
    subs_data = {
        "post": dict(post_elem.attrib),
        "events": [],
        "tables": [],
        "misc": [],
        "cancelled": [],
        "lessons": {}
    }

    def extract_data(elem: lxml.html.Element, next_elem: lxml.html.Element) -> None:
        """Extract the relevant information from each element in the post.

        Adds result to the subs_data dictionary.
        """

        if elem.tag == "table":
            # Check if any table headers have been found prior to the table element
            if len(subs_data["tables"]) == 0:
                # There hasn't; append a blank table object
                subs_data["tables"].append({
                    "title": "[Brak nagłówku tabeli]",
                    "headings": [],
                    "columns": []
                })
            extract_from_table(elem, subs_data["tables"][-1])
            return
        if elem.tag != "p":
            # Skip non-paragraph elements (i.e. comments, divs etc.)
            return
        # Check if this element has children
        child_elems = elem.xpath("./*")
        if child_elems:
            # The current element does have children
            if any(chld.tag != "strong" for chld in child_elems):
                # The child elements are not all bold tags
                return
            extract_header_data(elem, child_elems, subs_data)
        else:
            # The current element has no children
            elem_text: str = elem.text
            if not elem_text or not elem_text.strip():
                # Skip blank 'p' elements
                return
            if elem_text.lower().startswith("zajęcia z"):
                subs_data["cancelled"].append(elem_text)
                return
            if "są odwołane" in elem_text:
                # Ensure there is a trailing period
                if not elem_text.endswith("."):
                    elem_text += "."
                subs_data["cancelled"].append(elem_text)
                return
            # Check if this is the childless element right before a table tag
            if next_elem is not None and next_elem.tag == "table":
                # It is; assuming it's the element containing the table's title text
                subs_data["tables"].append({
                    "title": elem_text,
                    "headings": [],
                    "columns": []
                })
            else:
                # This is probably the actual substitutions text
                extract_substitutions_text(elem_text, subs_data)

    for i, p_elem in enumerate(post_elem):
        try:
            next_elem = post_elem[i + 1]
        except IndexError:
            next_elem = None
        try:
            # Attempt to extract the relevant data using a hard-coded algorithm
            extract_data(p_elem, next_elem)
        except (LookupError, TypeError, ValueError, AttributeError) as no_matches_exc:
            # Page structure has changed, return the nature of the error.
            if __name__ == "__main__":
                # Makes the error easier to see for debugging
                print(json.dumps(subs_data, indent=2, ensure_ascii=False),
                      f"\n{Colour.FAIL}Error encountered while processing child element "
                      f"{Colour.WARNING}{i + 1}{Colour.FAIL}!{Colour.ENDC}")
                raise no_matches_exc from None
            subs_data["error"] = ccutil.format_exception_info(no_matches_exc)
            break

    # Sort the lessons in ascending order
    unsorted_lessons = subs_data["lessons"]
    sorted_lessons = {}
    for key in sorted(unsorted_lessons.keys()):
        # Iterates through the lesson keys
        # Use string keys to facilitate JSON serialisation
        sorted_lessons[str(key)] = unsorted_lessons[key]
    subs_data["lessons"] = sorted_lessons

    # Return dictionary with substitution data
    return subs_data


def get_substitutions(force_update: bool = False) -> tuple[dict, dict]:
    """Gets the current lesson substitutions.

    Arguments:
        force_update -- a boolean indicating if the cache should be forcefully updated.

    Returns the data itself and a tuple containing the new and the old data (can be compared to
    check if the cache has changed).
    """
    def update_cache_callback() -> dict:
        html: str = web.get_html(SOURCE_URL, ignore_request_limit=force_update)
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
