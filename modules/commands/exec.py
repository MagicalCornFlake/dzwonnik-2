"""Module containing the code pertaining to the 'exec' command."""


# Standard library imports
import ast
import json

# Third-party imports
import discord

# Local application imports
from .. import bot, util


DESC = None
MISSING_PERMS_MSG = "synchronicznego egzekowania kodu"
MISSING_ARGUMENTS_MSG = "Type an expression or command to execute."

# Initialise the code template to execute when the 'exec' command is called.
EXPRESSION_TEMPLATE = "async def _execute():\n    {}\n\nlocals()['_execute'] = _execute"


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


def inject_code(expression: str) -> str:
    """Attempts to inject code so that the evaluation result of the expression is saved in memory.

    Arguments:
        expression -- a string containing the raw code to be executed.

    Returns a string that may or may not contain injected code, depending on the input structure.
    """
    if "return " in expression:
        # Inject temp variable storage in place of 'return' statements
        injection_snippet = "locals()['temp'] += "
        expression = expression.replace("return ", injection_snippet)
        expression = f"""locals()['temp'] = ExecResultList()\n{expression}"""
    else:
        # No user-specified return value
        # Attempt to inject code so that the evaluation of the first line is returned
        try:
            # Check if such a code injection would be valid Python code
            ast.parse("locals()['temp'] = " + expression)
        except SyntaxError as syntax_error:
            # Code injection raises a syntax error; ignore it and don't inject code
            fmt_exc = util.format_exception_info(syntax_error)
            bot.send_log(f"Caught SyntaxError in code injection:\n\n{fmt_exc}")
        else:
            # No syntax error; initialise the 'temp' local variable in code injection
            expression = f"locals()['temp'] = {expression}"

    expression = EXPRESSION_TEMPLATE.format(expression.replace("\n", "\n    "))
    bot.send_log(f"Executing code:\n{expression}", force=True)
    return expression


async def process_execution(message: discord.Message) -> str:
    """Executes the code and returns the message that should be sent to the user.

    Arguments:
        expression -- the raw expression to be executed.

    Returns the message that should be sent back directly to the user.
    """
    msg_content: str = message.content
    expression = msg_content.split(" ", maxsplit=1)[1]

    try:
        # Inject result-storing code to the user input and execute it
        exec(inject_code(expression))  # pylint: disable=exec-used
        await locals()["_execute"]()
    except Exception as exec_exc:  # pylint: disable=broad-except
        # If the code logic is malformed or otherwise raises an exception, return the error info.
        exec_result = util.format_exception_info(exec_exc)
    else:
        # Default the temp variable to an empty ExecResultList if it's not been assigned
        exec_result = locals().get("temp", ExecResultList())

        # Check if the results list is empty
        if isinstance(exec_result, ExecResultList) and not exec_result:
            return "*(return value unspecified)*"
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
    return f"```py\n{results}```"


def exec_command_handler(message: discord.Message) -> tuple[bool, str]:
    """Event handler for the 'exec' command."""
    msg_content: str = message.content
    args = msg_content.split(' ', maxsplit=1)
    if message.author != bot.client.get_user(bot.MEMBER_IDS[8 - 1]):
        raise bot.MissingPermissionsException(MISSING_PERMS_MSG)
    try:
        expression = args[1]
    except IndexError:
        return False, MISSING_ARGUMENTS_MSG
    fmt_expr = expression.replace("\n", "\n>>> ")
    return False, f"Code executing...\n```py\n>>> {fmt_expr}```"


async def execute_code(original_msg: discord.Message, reply_msg: discord.Message) -> None:
    """Callback function for the 'exec' command. Executes after the bot replies initially."""
    if reply_msg.content == MISSING_ARGUMENTS_MSG:
        return
    chnl: discord.TextChannel = reply_msg.channel
    async with chnl.typing():
        exec_result = await process_execution(original_msg)
    new_content = reply_msg.content.replace("executing...", "executed!")
    await reply_msg.edit(content=new_content)
    await reply_msg.channel.send(content=exec_result)
