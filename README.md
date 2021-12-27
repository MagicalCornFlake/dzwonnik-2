<!-- omit in toc -->
# Table of Contents 

- [About Dzwonnik 2](#about-dzwonnik-2)
  - [Libraries](#libraries)
- [Usage](#usage)
  - [Commands](#commands)
    - [General commands (incomplete)](#general-commands-incomplete)
      - [help](#help)
      - [nl](#nl)
      - [nb](#nb)
    - [Administrator commands](#administrator-commands)
      - [meet](#meet)
    - [Developer commands](#developer-commands)
      - [restart](#restart)
      - [exit](#exit)
      - [exec](#exec)
- [Todo](#todo)

# About Dzwonnik 2
A Discord bot made in Python for personal use by Konrad Guzek.

## Libraries
Dzwonnik 2 was created using **discord.py**, the official library for creating Discord bots in Python. The list of used built-in modules is as follows:
 - asyncio
 - datetime
 - importlib
 - json
 - math
 - os
 - re
 - requests
 - time
 - traceback
 - urllib

Dzwonnik 2 additionally uses some third-party libraries to complete specific tasks:
 - lxml (in particular the `HTML` module)

# Usage
Dzwonnik 2 is a Discord bot intended to be used on Konrad Guzek's school Discord server. The server's ID is hard-coded into the module constants, however with modifications it would be able to run on other severs as well. The default command prefix is `!`, but its usage in the code is extremely organised so with a single modification the prefix could be changed to any string. Note that there is currently no built-in command for changing the prefix, however there is a command for executing python code accessible to the sever owner.

## Commands
Dzwonnik 2 contains a `help` command which outlines all the commands that are available to the general users. The help message may also be sent whenever a user __@mentions__ the bot.

### General commands (incomplete)
These are the commands intented for use by the average user.

#### help
The `help` command replies to the caller with the current prefix for commands as well as a list of available commands. The message also triggers when somebody __@mentions__ Dzwonnik 2.

#### nl
The `nl` command replies with information about the next lesson. By default, it does this for the current time. The bot checks what the next period is according to the timetable, and then looks at any lessons that are in the lesson plan for that day on that period. If there aren't any, the bot continues to look for lessons on the next school day (if the next day is on the weekend, it looks at Monday). Next, the bot checks if any of the lessons are for Group 0 (i.e. the entire class). If there any such lessons, it compares the roles of the calling user with the specified groups for the found lessons. 
Finally, when a lesson is found, the bot provides the name of the lesson, the time of the lesson (as well as the day of the week if that isn't today) and a countdown to show how much time there is until the start of the lesson. This countdown is not live -- it is only current as of the time the message was sent. Next, the bot checks if there was a Google Meet link set for the lesson, and if so, it sends the link as well.

#### nb
The `nb` command works similarly to the `nl` command in how it checks for the next period, however it sends information about when the current period ends. If it's currently breaktime, it checks for information after the next break after this one. Just like the `nl` command, it sends information about the timespan of the break as well as a static countdown to its start. If it's the last break for the given day (so there are no lessons after the break), it also reports that information. 

### Administrator commands
These commands are special commands that do not appear in the help message. They only change surface settings, so in theory they are safe to use by any user, however they have been restricted to users with the *administrator* permission by default to prevent accidental typos and misuse.

#### meet
The `meet` command allows users to view all currently set Google Meet links for each lesson. This feature is accessible to every user by default. Also, if a lesson name is specified after this command, the bot only responds with the link set for that specific lesson. However, if after a lesson name there is a Meet link specified, the bot changes the link that is saved for that lesson. This feature is only for administrators by default.

### Developer commands
These commands are hard-coded to only be available to Konrad Guzek, but the user ID may be changed in the code to allow for a specific user to use them. They are dangerous commands that directly impact the functionality of the bot.

#### restart
One of the most useful commands in development, the `restart` command completely restarts the bot. This works as the bot is run from a `run.pyw` file that contains an infinite loop that reloads the `main` module and runs it until it finishes executing. The `restart` command terminates the module, which means the loop is progressed and any changes are reloaded using `importlib`. 

#### exit
The `exit` command is similar to the `restart` command in that it terminates the `main` module, however it indicates that the run loop should not continue to run.
The main `start_bot` funciton returns a boolean, and if that boolean is false, the loop in `run.pyw` breaks. In essence, this command completely terminates the bot program.

#### exec
The `exec` command allows the calling user to execute valid Python code as if it were in a terminal window. The evaluated values are sent back to the user, the same way as in the Python shell. However, for more complex code, the user may use a `return` statement to indicate what value should be returned to the user. `return` statements used in code executed by this command are not treated like they are under normal Python execution.

# Todo
Dzwonnik 2's main functionality is fully implemented, however there are always ways to improve a program.

* Implement a command for changing the bot command prefix
* General refactorings to separate `main.py` into many smaller modules
* Finish README.md (commands list is incomplete)
* Add better docstrings and general commented documentation in the source code