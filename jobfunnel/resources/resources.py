"""Constant definitions or files we need to load once can go here
"""
import os


CSV_HEADER = [
    'status', 'title', 'company', 'location', 'date', 'blurb', 'tags', 'link',
    'id', 'provider', 'query', 'locale'
]  # TODO: need to add short and long descriptions (breaking change)


USER_AGENT_LIST_FILE = os.path.normpath(
    os.path.join(os.path.dirname(__file__), 'user_agent_list.txt')
)


USER_AGENT_LIST = []
with open(USER_AGENT_LIST_FILE) as file:
    for line in file:
        li = line.strip()
        if li and not li.startswith("#"):
            USER_AGENT_LIST.append(line.rstrip('\n'))
