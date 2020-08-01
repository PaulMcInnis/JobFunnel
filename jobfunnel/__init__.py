import os
import random


__version__ = '2.1.9'


# FIXME: gotta be a better way...
USER_AGENT_LIST_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), 'text/user_agent_list.txt'))
USER_AGENT_LIST = []
with open(USER_AGENT_LIST_FILE) as file:
    for line in file:
        li = line.strip()
        if li and not li.startswith("#"):
            USER_AGENT_LIST.append(line.rstrip('\n'))
