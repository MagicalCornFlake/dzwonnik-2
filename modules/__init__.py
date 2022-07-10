"""
__init__.py file for the general modules containing definitions for constant values
that are used repeatedly in the program.
"""


class Colour:
    """Constant definitions for colours used in the console."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class Emoji(str):
    """Constant definitions for Discord message emoji."""

    CASH: str = ":moneybag:"
    CHECK: str = ":white_check_mark:"
    CHECK_2: str = ":ballot_box_with_check:"
    INFO: str = ":information_source:"
    WARNING: str = ":warning:"

    UNICODE_ALARM_CLOCK: str = "\N{ALARM CLOCK}"
    UNICODE_CHECK: str = "\N{BALLOT BOX WITH CHECK}"
    UNICODE_DETECTIVE: str = "\N{SLEUTH OR SPY}"


class Weekday(int):
    """Constant definitions for the integers corresponding to each day of the week."""

    MONDAY: int = 0
    TUESDAY: int = 1
    WEDNESDAY: int = 2
    THURSDAY: int = 3
    FRIDAY: int = 4
    SATURDAY: int = 5
    SUNDAY: int = 6


class Month(int):
    """Constant declarations for the months of the year."""

    JANUARY: int = 1
    FEBRUARY: int = 2
    MARCH: int = 3
    APRIL: int = 4
    MAY: int = 5
    JUNE: int = 6
    JULY: int = 7
    AUGUST: int = 8
    SEPTEMBER: int = 9
    OCTOBER: int = 10
    NOVEMBER: int = 11
    DECEMBER: int = 12


WEEKDAY_NAMES = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"]

# What group code correlates to which Discord role
ROLE_CODES = {
    "grupa_0": "everyone",
    "grupa_1": "Grupa 1",
    "grupa_2": "Grupa 2",
    "grupa_rel": "Religia",
    "grupa_2fp": "Język Francuski",
    "grupa_2hp": "Język Hiszpański",
    "grupa_2np": "Język Niemiecki (Podstawa)",
    "grupa_2pn": "Język Niemiecki (Rozszerzenie)",
    "grupa_RB": "Biologia Rozszerzona",
    "grupa_RCH": "Chemia Rozszerzona",
    "grupa_RH": "Historia Rozszerzona",
    "grupa_RG": "Geografia Rozszerzona",
    "grupa_RF": "Fizyka Rozszerzona",
}

# Dictionary with text to use when sending messages, e.g. 'lekcja dla grupy drugiej'
GROUP_NAMES = {
    "grupa_0": "",
    "grupa_1": "dla grupy pierwszej",
    "grupa_2": "dla grupy drugiej",
    "grupa_rel": "dla grupy religijnej",
    "grupa_2fp": "dla grupy francuskiej",
    "grupa_2hp": "dla grupy hiszpańskiej",
    "grupa_2np": "dla grupy niemieckiej z podstawą",
    "grupa_2pn": "dla grupy niemieckiej z rozszerzeniem",
    "grupa_RB": "dla rozszerzenia z biologii",
    "grupa_RCH": "dla rozszerzenia z chemii",
    "grupa_RH": "dla rozszerzenia z historii",
    "grupa_RG": "dla rozszerzenia z geografii",
    "grupa_RF": "dla rozszerzenia z fizyki",
}


# noinspection SpellCheckingInspection
MEMBER_IDS = [
    693443232415088650,  # 01 Zofia Cybul
    695209819715403818,  # 02 Aleksandra Cywińska
    690174699459706947,  # 03 Ida Durbacz
    770552880791814146,  # 04 Pola Filipkowska
    773113923485827103,  # 05 Hanna Frej
    626494841865633792,  # 06 Adam Górecki
    622560689893933066,  # 07 Anna Grodnicka
    274995992456069131,  # 08 Konrad Guzek
    775676246566502400,  # 09 Aleksandra Izydorczyk
    690174919874576385,  # 10 Emilia Kiełkowska
    690171714025553924,  # 11 Maja Kierzkowska
    566344296001830923,  # 12 Zofia Kokot
    689859486172971082,  # 13 Stanisław Krakowian
    690171664062873721,  # 14 Daria Luszawska
    690275577835290684,  # 15 Martyna Marszałkowska
    770183107348529183,  # 16 Lena Masal
    692691918986936320,  # 17 Kalina Maziarczyk
    769604750898757662,  # 18 Mateusz Miodyński
    "Amelia Sapota",  # 19 Amelia Sapota
    770183024339714068,  # 20 Zofia Smołka
    770552880791814146,  # 21 Aleksandra Sobczyk
    626490320401596437,  # 22 Klara Sokół
    366955740260335646,  # 23 Krzysztof Szatka
    772888760340971531,  # 24 Iga Śmietańska
    635244325344772119,  # 25 Wojciech Tutajewicz
    770630571457380373,  # 26 Magdalena Wacławczyk
    694831920013639732,  # 27 Oliwia Wężyk
    715163616474693662,  # 28 Natalia Wcisło
    585427549216047104,  # 29 Paweł Żuchowicz
    712656114247794700,  # 20 Katarzyna Klos
    910219602552840202,  # 31 Patrycja Tustanowska
]
