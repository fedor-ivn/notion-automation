from third_party.notion.client import NotionClient
from os import getenv
import logging

logger = logging.getLogger('notion')
logger.setLevel(logging.DEBUG)

TOKEN = getenv('TOKEN_V2')
client = NotionClient(token_v2=TOKEN)
TASKS_TABLE_URL = 'https://www.notion.so/fedorivn/f1679ab27ce74e62b8cf14b26a45857c?v=56426b29cbc74140bd53f117030ff80a'


def main():
    default = 'Inbox task text was not specified.'
    task_text = getenv('INBOX_TASK_TEXT', default)
    tasks_table = client.get_collection_view(TASKS_TABLE_URL)
    new_entry = tasks_table.collection.add_row()
    new_entry.task = task_text


if __name__ == '__main__':
    main()
