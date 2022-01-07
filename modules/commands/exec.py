"""Module containing the code pertaining to the 'exec' and 'exec_async' commands."""


# Standard library imports
import json

# Third-party imports
import discord

# Local application imports
from .. import bot, util


DESC = None


class ExecResultList(list):
    """Defines a custom class that derives from the `list` base type.
    This class redefines the += operator to append new items rather than merge lists.
    """

    def __init__(self):
        super().__init__(self)

    def __iadd__(self, __x):
        """Appends an item to the list."""
        self.append(__x)
        return self


def execute_sync(message: discord.Message) -> tuple[bool, str or discord.Embed]:
    """Event handler for the 'exec' command."""
    if message.author != bot.client.get_user(bot.MEMBER_IDS[8 - 1]):
        missing_perms_msg = "synchronicznego egzekowania kodu"
        raise bot.MissingPermissionsException(missing_perms_msg)
    msg_content: str = message.content
    args = msg_content.split(' ', maxsplit=1)
    try:
        expression = args[1]
    except IndexError:
        return False, "Type an expression or command to execute."
    try:
        if "return " in expression:
            injected_code = expression.replace("return ", "locals()['temp'] += ")
            expression_to_be_executed = f"""ExecResultList()\n{injected_code}"""
        else:
            expression_to_be_executed = expression
        try:
            exec("locals()['temp'] = " + expression_to_be_executed)
            execing = "Executing injected code:\nlocals()['temp'] =", expression_to_be_executed
            bot.send_log(*execing, force=True)
        except SyntaxError as ex:
            bot.send_log("Caught SyntaxError in 'exec' command:", force=True)
            bot.send_log(util.format_exception_info(ex), force=True)
            bot.send_log("Executing raw code:\n" + expression, force=True)
            exec(expression)
    except Exception as ex:
        exec_result = util.format_exception_info(ex)
    else:
        exec_result = locals().get("temp")
    bot.send_log(f"Temp variable: {exec_result}")
    if not exec_result:
        return False, "Code executed (return value not specified)."
    res_msg = []
    json_responses = []
    for res in exec_result if isinstance(exec_result, ExecResultList) else [exec_result]:
        json_responses.append("")
        if type(res) in [list, dict, tuple]:
            try:
                # Add the index of the current result to the list of JSON result indicies
                json_responses.append(len(res_msg))

                tmp = json.dumps(res, indent=2, ensure_ascii=False)
                res_msg.append(tmp)
            except (TypeError, OverflowError):
                res_msg.append(str(res))
        else:
            res_msg.append(str(res))

    def fmt_res(index: int) -> str:
        """Util function for formatting the returned result.
        If the result has been marked as JSON content, 'detected JSON content' is prepended.
        """
        result = res_msg[index]
        if index in json_responses:
            result = "```\nDetected JSON content:```json\n" + result
        return result

    fmt_expr = expression.replace("\n", "\n>>> ")
    res_msg = "\n".join([fmt_res(i) for i in range(len(res_msg))])

    return False, f"Code executed:\n```py\n>>> {fmt_expr}\n{res_msg}```"


def execute_async(message: discord.Message) -> tuple[bool, str or discord.Embed]:
    """Event handler for the 'exec_async' command."""
    if message.author != bot.client.get_user(bot.MEMBER_IDS[8 - 1]):
        raise bot.MissingPermissionsException(
            "asynchronicznego egzekowania kodu")
    return False, ""


async def run_async_code(_original_msg: discord.Message, _reply_msg: discord.Message) -> None:
    """Executes code asynchronously."""
