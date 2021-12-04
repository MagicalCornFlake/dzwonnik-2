"""Definitions for constant values that are used repeatedly in the program"""


__all__ = ["ChannelID", "RoleID", "Emoji"]


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
