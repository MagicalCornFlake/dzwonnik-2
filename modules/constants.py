"""Definitions for constant values that are used repeatedly in the program"""


__all__ = ["my_server_id", "ChannelID", "RoleID", "Emoji",
           "Weekday", "weekday_names", "role_codes", "group_names", "member_ids"]


my_server_id: int = 766346477874053130


class ChannelID:
    general: int = 766346477874053132
    nauka: int = 769098845598515220
    admini: int = 773137866338336768
    bot_testing: int = 832700271057698816
    bot_logs: int = 835561967007432784


class RoleID:
    gr1: int = 766346710712582155
    gr2: int = 766346737400807474


class Emoji:
    check: str = ":white_check_mark:"
    info: str = ":information_source:"
    warning: str = ":warning:"

    unicode_alarm_clock: str = "\N{ALARM CLOCK}"
    unicode_check: str = "\N{BALLOT BOX WITH CHECK}"
    unicode_detective: str = "\N{SLEUTH OR SPY}"


class Weekday:
    monday: int = 0
    tuesday: int = 1
    wednesday: int = 2
    thursday: int = 3
    friday: int = 4
    saturday: int = 5
    sunday: int = 6


weekday_names = [
    "poniedziałek",
    "wtorek",
    "środa",
    "czwartek",
    "piątek",
    "poniedziałek",  # When get_next_lesson() is called on Saturday or Sunday,
    "poniedziałek"  # the program looks at Monday as the next school day.
]

# What group code correlates to which Discord role
role_codes = {
    "grupa_0": "everyone",
    "grupa_1": "Grupa 1",
    "grupa_2": "Grupa 2",
    "grupa_rel": "Religia",
    "grupa_es": "Język Hiszpański",
    "grupa_fr": "Język Francuski",
    "grupa_de1": "Język Niemiecki (Podstawa)",
    "grupa_de2": "Język Niemiecki (Rozszerzenie)",
    "grupa_bio": "Rozszerzenie z biologii",
    "grupa_chem": "Rozszerzenie z chemii",
    "grupa_his": "Rozszerzenie z historii",
    "grupa_geo": "Rozszerzenie z geografii",
    "grupa_fiz": "Rozszerzenie z fizyki"
}

# Dictionary with text to use when sending messages, eg. 'lekcja dla grupy drugiej'
group_names = {
    "grupa_0": "",
    "grupa_1": "dla grupy pierwszej",
    "grupa_2": "dla grupy drugiej",
    "grupa_rel": "dla grupy religijnej",
    "grupa_es": "dla grupy hiszpańskiej",
    "grupa_fr": "dla grupy francuskiej",
    "grupa_de1": "dla grupy niemieckiej z podstawą",
    "grupa_de2": "dla grupy niemieckiej z rozszerzeniem",
    "grupa_bio": "dla rozszerzenia z biologii",
    "grupa_chem": "dla rozszerzenia z chemii",
    "grupa_his": "dla rozszerzenia z historii",
    "grupa_geo": "dla rozszerzenia z geografii",
    "grupa_fiz": "dla rozszerzenia z fizyki"
}


# noinspection SpellCheckingInspection
member_ids = [
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
    "Amelia Sapota",     # 19 Amelia Sapota
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
