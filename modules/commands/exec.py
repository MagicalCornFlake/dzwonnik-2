"""Module containing the code pertaining to the 'exec' and 'exec_async' commands."""


# Standard library imports
import ast
import json

# Third-party imports
import discord

# Local application imports
from .. import bot, util


DESC = None
MISSING_PERMS_MSG_SYNC = "synchronicznego egzekowania kodu"
MISSING_PERMS_MSG_ASYNC = "asynchronicznego egzekowania kodu"


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
        raise bot.MissingPermissionsException(MISSING_PERMS_MSG_SYNC)
    msg_content: str = message.content
    args = msg_content.split(' ', maxsplit=1)
    try:
        expression = args[1]
    except IndexError:
        return False, "Type an expression or command to execute."
    else:
        fmt_expr = expression.replace("\n", "\n>>> ")
        result_template = f"Code executed:\n```py\n>>> {fmt_expr}\n{{}}"

    if "return " in expression:
        # Inject temp variable storage in place of 'return' statements
        inj_snippet = "locals()['temp'] += "
        injected_code = expression.replace("return ", inj_snippet)
        expression_to_be_executed = f"""locals()['temp'] = ExecResultList()\n{injected_code}"""
    else:
        # No user-specified return value
        # Attempt to inject code so that the evaluation of the first line is returned
        try:
            # Check if such a code injection would be valid Python code
            ast.parse("locals()['temp'] = " + expression)
        except SyntaxError as syntax_error:
            # Code injection raises a syntax error; ignore it and don't inject code
            fmt_exc = util.format_exception_info(syntax_error)
            caught_exc_msg = f"Caught SyntaxError in code injection:\n\n{fmt_exc}"
            bot.send_log(caught_exc_msg, force=True)

            # Execute the code without temp variable assignment
            expression_to_be_executed = expression
        else:
            # No syntax error; initialise the 'temp' local variable in code injection
            expression_to_be_executed = f"locals()['temp'] = {expression}"

    executing_log_msg = f"Executing code:\n{expression_to_be_executed}"
    bot.send_log(executing_log_msg, force=True)

    try:
        # Actually execute the code
        exec(expression_to_be_executed)
    except Exception as exec_exc:
        # If the code logic is malformed or otherwise raises an exception, return the error info.
        exec_result = util.format_exception_info(exec_exc)
    else:
        # Default the temp variable to an empty ExecResultList if it's not been assigned
        exec_result = locals().get("temp", ExecResultList())

        # Check if the results list is empty
        if isinstance(exec_result, ExecResultList) and not exec_result:
            return False, result_template.format("```(return value was not specified)")
    temp_variable_log_msg = f"Temp variable ({type(exec_result)}):\n{exec_result}"
    bot.send_log(temp_variable_log_msg, force=True)
    results = []
    json_result_indices = []
    for res in exec_result if isinstance(exec_result, ExecResultList) else [exec_result]:
        json_result_indices.append("")
        if type(res) in [list, dict, tuple]:
            try:
                # Add the index of the current result to the list of JSON result indices
                json_result_indices.append(len(results))

                tmp = json.dumps(res, indent=2, ensure_ascii=False)
                results.append(tmp)
            except (TypeError, OverflowError):
                results.append(str(res))
        else:
            results.append(str(res))

    def fmt_res(index: int) -> str:
        """Util function for formatting the returned result.

        If the result has been marked as JSON content, prepends 'detected JSON content' to it.
        """
        result = results[index]
        if index in json_result_indices:
            result = "```\nDetected JSON content:```json\n" + result
        return result

    results = "\n".join([fmt_res(i) for i in range(len(results))])

    return False, result_template.format(results + "```")


def execute_async(message: discord.Message) -> tuple[bool, str or discord.Embed]:
    """Event handler for the 'exec_async' command."""
    if message.author != bot.client.get_user(bot.MEMBER_IDS[8 - 1]):
        raise bot.MissingPermissionsException(MISSING_PERMS_MSG_ASYNC)
    return False, ""


async def run_async_code(_original_msg: discord.Message, _reply_msg: discord.Message) -> None:
    """Executes code asynchronously."""
