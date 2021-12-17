"""Functionality for scraping the data from lo1.gliwice.pl website to retrieve lesson plan details"""


def get_plan_id(class_name: str) -> int:
    # noinspection SpellCheckingInspection
    letters = "abcde"
    try:
        class_year = int(class_name[0])
        class_letter = class_name[1]
        if not 1 <= class_year <= 3:
            raise ValueError
        # 3 is the number of classes in year 3 that are type "g" (gimnazjum)
        # 6 and 5 are the numbers of classes in year 3 and 2, respectively
        base_id = letters.index(class_letter.lower()) + 1
        return base_id + ((3 * (class_name[2].lower() == "p")) if class_year == 3 else (6 + 5 * (class_year == 1)))
    except (ValueError, IndexError):
        raise ValueError("Invalid class name.")


def get_plan_link(class_id: int) -> str:
    return f"http://www.lo1.gliwice.pl/wp-content/uploads/static/plan/plany/o{class_id}.html"


def parse_html(html: str):
    for row in html.splitlines():
        print(row)


if __name__ == "__main__":
    import web_api
    try:
        while True:
            link: str = get_plan_link(get_plan_id(input("Enter class name...\n> ")))
            print("Link:", {link})
            res = web_api.make_request(link).content.decode('UTF-8')
            parse_html(res)
    except KeyboardInterrupt:
        print("Goodbye!")
