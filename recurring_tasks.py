from datetime import datetime, timedelta

from third_party.notion.client import NotionClient
from os import getenv
from dateutil.relativedelta import *

from third_party.notion.collection import NotionDate

TOKEN = getenv('TOKEN_V2')
client = NotionClient(token_v2=TOKEN)
TASKS_TABLE_URL = 'https://www.notion.so/fedorivn/f1679ab27ce74e62b8cf14b26a45857c?v=56426b29cbc74140bd53f117030ff80a'
TIME_TABLE_URL = 'https://www.notion.so/fedorivn/8ff691cd5d744a6186ae66b4e0d2d195?v=896b6dd1c5d9476690c50babf54d0079'


def calculate_next_repeat(row):
    kwargs = {
        row.interval_type: row.interval
    }
    return row.last_repeat.start + relativedelta(**kwargs)


def recurring_task_process(row, next_repeat, tasks_table):
    entry = row.task[0]
    new_entry = tasks_table.collection.add_row()

    new_entry.due_date = NotionDate(next_repeat)
    new_entry.task = entry.task
    new_entry.priority = entry.priority
    if entry.context:
        new_entry.context = entry.context
    new_entry.status = 'todo'
    new_entry.project = entry.project
    new_entry.related_tasks = entry.related_tasks
    new_entry.parent_task = entry.parent_task
    new_entry.files = entry.files

    row.task = [new_entry]
    row.last_repeat = NotionDate(next_repeat)


def ensure_datetime(d):
    """
    Takes a date or a datetime as input, outputs a datetime
    """
    if isinstance(d, datetime):
        return d
    return datetime(d.year, d.month, d.day)


def main():
    time_table = client.get_collection_view(TIME_TABLE_URL)
    tasks_table = client.get_collection_view(TASKS_TABLE_URL)

    # todo: там внутри полный треш, исправить
    #  third_party/notion/collection.py
    query = time_table.build_query()
    recurring_tasks = query.execute()

    print(len(recurring_tasks))
    print(recurring_tasks)

    # todo: и здесь тоже
    #  third_party/notion/store.py
    # row = cv.collection.add_row()

    for row in recurring_tasks:
        print(row.task)
        if not row.active:
            continue
        next_repeat = calculate_next_repeat(row)
        if ensure_datetime(next_repeat) - datetime.now() <= timedelta(minutes=30):
            recurring_task_process(row, next_repeat, tasks_table)


if __name__ == '__main__':
    main()
