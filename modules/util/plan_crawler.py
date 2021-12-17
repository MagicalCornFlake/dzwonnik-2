"""Functionality for scraping the data from lo1.gliwice.pl website to retrieve lesson plan details"""

def get_plan_id(class_name: str) -> int:
    letters = "abcde"
    try:
        class_year = int(class_name[0])
        class_letter = class_name[1]
        if not 1 <= class_year <= 3:
            raise ValueError
        # 3 is the number of classes in year 3 that are type "g" (gimnazjum)
        # 6 and 5 are the numbers of classes in year 3 and 2, respectively
        if class_year == 3:
            print("Class 3")
            return letters.index(class_letter) + 1 + (3 * class_name[2] == "p")
        else:
            print("Not 3")
            return letters.index(class_letter) + 1 + (6 + 5 * class_year == 1) 
    except (ValueError, IndexError):
        raise ValueError("Invalid class name.")


def get_plan_link(class_id: int) -> str:
    return f"http://www.lo1.gliwice.pl/wp-content/uploads/static/plan/plany/o{class_id}.html"


if __name__ == "__main__":
    try:
        while True:
            plan_id: int = get_plan_id(input("Enter class name...\n> "))
            print(f"Plan ID: {plan_id}")
            print(f"Link: {get_plan_link(plan_id)}")
    except KeyboardInterrupt:
        print("Goodbye!")