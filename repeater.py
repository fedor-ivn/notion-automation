"""
todo:
    - logging
    - pagination logic processing
"""
import os
from datetime import datetime, timedelta
from typing import List

import isodate
import dateutil
from dotenv import load_dotenv
from notion_client import Client
import croniter

load_dotenv()
TIMEZONE = 'Europe/Moscow'
NOTION_API_TOKEN = os.environ['NOTION_API_TOKEN']
TASK_TEMPLATE_DATABASE_ID = os.environ['TASK_TEMPLATE_DATABASE_ID']
TASK_REPEATER_DATABASE_ID = os.environ['TASK_REPEATER_DATABASE_ID']
TASK_DATABASE_ID = os.environ['TASK_DATABASE_ID']
TIMEDELTA_IN_MINUTES = 5


class BaseNotionPage:
    def __init__(self, client: Client, data: dict = None, page_id: str = None):
        self.client = client
        if data:
            self.data = data
        elif page_id:
            self.data = self.client.pages.retrieve(page_id=page_id)
        else:
            raise ValueError('Either data or page_id should be provided.')

    @property
    def page_id(self) -> str:
        return self.data['id']

    @property
    def properties(self) -> dict:
        return self.data['properties']

    def get_relation_ids(self, field_name):
        return [rel['id'] for rel in self.properties[field_name]['relation']]


class RenderError(Exception):
    pass


class TaskTemplate(BaseNotionPage):
    ID_REMOVING_EXCLUDE_FIELDS = ['relation']
    # Name (in templates) -> id (in tasks)
    NAME_REPLACING_FIELDS_MAPPING = {
        'Name': 'title',
        'Due date': '\\}q:',
        'Priority': 'OLUC',
        'Status': 'fVTo',
        'Context': 'NmA]',
        'Project': 'sX=q',
        'URL': 'Y?lD',
        # 'Files': ':6cK',
        'Notes': 'Rocm',
        'Parent task': 'xs=Y',
        'Related tasks': 'gg;y',
    }
    DURATION_STRING_ALIASES = {
        '@immediately': 'P0D',
        '@week': 'P7D',
        '@day': 'P1D',
        '@hour': 'PT1H'
    }

    def __init__(self, client: Client, start_date: datetime, data: dict = None, page_id=None):
        super().__init__(client, data, page_id)
        self.start_date = start_date

    @property
    def name(self):
        return self.properties['Name']['title'][0]['plain_text']

    @classmethod
    def recursive_id_removing(cls, data: dict):
        if 'id' in data:
            del data['id']

        for key, value in data.items():
            if key in cls.ID_REMOVING_EXCLUDE_FIELDS:
                continue
            elif isinstance(value, dict):
                cls.recursive_id_removing(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        cls.recursive_id_removing(item)

    def render_related_tasks(self) -> List[BaseNotionPage]:
        """
        Renders all related tasks and returns list of ids
        """
        related_template_ids = self.get_relation_ids('Related tasks')
        res = []
        for template_id in related_template_ids:
            template = TaskTemplate(
                self.client,
                start_date=self.start_date,
                page_id=template_id
            )
            task = template.render()
            res.append(task)
        return res

    def get_task_date(self):
        duration_field = self.properties.get('Duration after repeat (ISO 8601)')
        if not duration_field:
            return

        duration_string = duration_field['select']['name']
        if duration_string in self.DURATION_STRING_ALIASES:
            duration_string = self.DURATION_STRING_ALIASES[duration_string]

        date = self.start_date + isodate.parse_duration(duration_string)
        # noinspection PyUnresolvedReferences
        date = date.replace(tzinfo=dateutil.tz.gettz(TIMEZONE))

        # optimize datetime object for Notion representation
        if date.time().isoformat() == '00:00:00':
            date = date.date()

        print(date.isoformat())
        return date

    def build_task_properties(self):
        """
        Builds properties of the task and renders related tasks
        """
        props_copy = self.properties.copy()
        self.recursive_id_removing(props_copy)

        related_tasks = self.render_related_tasks()
        relation = [{'id': t.page_id} for t in related_tasks]
        props_copy['Related tasks']['relation'] = relation

        task_date = self.get_task_date()
        if task_date:
            props_copy['Due date'] = {
                'date': {
                    'start': task_date.isoformat()
                }
            }

        # todo: additional processing and recursive rendering on this fields
        unsupported_fields = ['Files']
        keys_to_delete = ['Task repeater', 'Parent task', 'Duration after repeat (ISO 8601)']
        for key in keys_to_delete + unsupported_fields:
            if key in props_copy:
                del props_copy[key]

        print(props_copy)

        for old_name, new_id in self.NAME_REPLACING_FIELDS_MAPPING.items():
            if old_name in props_copy:
                props_copy[new_id] = props_copy.pop(old_name)

        return props_copy

    def get_prepared_child(self, child: dict) -> dict:
        """
        Includes only necessary fields, ignoring fields like `id`, `created_time`, etc.
        """
        block_type = child['type']
        if block_type == 'unsupported':
            raise RenderError(
                f'Template "{self.name}" contains unsupported blocks. You should remove them.'
            )
        include_fields = ['object', 'type', block_type]
        return {
            key: child[key] for key in include_fields
        }

    def get_page_content(self):
        children_data = self.client.blocks.children.list(block_id=self.page_id)
        children = children_data['results']
        return [self.get_prepared_child(child) for child in children]

    def render(self):
        props = self.build_task_properties()
        content = self.get_page_content()

        task_page_data = self.client.pages.create(
            parent={
                'database_id': TASK_DATABASE_ID
            },
            properties=props
        )
        print(task_page_data)
        task_page = BaseNotionPage(self.client, task_page_data)
        children = self.client.blocks.children.append(
            task_page.page_id,
            children=content
        )
        print(children)
        return task_page


class TaskRepeater(BaseNotionPage):
    def __init__(self, client: Client, data: dict = None, page_id: str = None):
        super().__init__(client, data, page_id)

        # in select field comma character is not allowed, so we use ';' instead
        schedule = self.properties['Crontab']['select']['name'].replace(';', ',')

        last_repeat = datetime.fromisoformat(self.properties['Last repeat']['date']['start'])
        cron = croniter.croniter(schedule, last_repeat, ret_type=datetime)
        self.next_repeat = cron.get_next()
        self.next_next_repeat = cron.get_next()

    @property
    def is_active(self):
        return self.properties['Active']['checkbox']

    def should_be_executed(self) -> bool:
        return self.next_repeat - datetime.now() <= timedelta(minutes=TIMEDELTA_IN_MINUTES)

    def update_date_field(self, date, property_name):
        # optimize datetime object for Notion representation
        if date.time().isoformat() == '00:00:00':
            date = date.date()

        self.client.pages.update(
            self.page_id,
            properties={
                property_name: {
                    'date': {
                        'start': date.isoformat()
                    }
                }
            }
        )

    def update_last_repeat(self):
        self.update_date_field(self.next_repeat, 'Last repeat')

    def execute(self):
        self.update_date_field(self.next_repeat, 'Next repeat')

        if not (self.is_active and self.should_be_executed()):
            print('Should not be executed. Skipping...')
            return

        for template_id in self.get_relation_ids('Templates'):
            template = TaskTemplate(
                self.client,
                start_date=self.next_repeat,
                page_id=template_id
            )
            template.render()

        self.update_last_repeat()
        self.update_date_field(self.next_next_repeat, 'Next repeat')


def run_repeaters():
    client = Client(auth=NOTION_API_TOKEN)

    repeaters_data = client.databases.query(
        TASK_REPEATER_DATABASE_ID,
        filter={
            "property": "Active",
            "checkbox": {
                "equals": True
            }
        }
    )

    repeaters = [TaskRepeater(client, data=data) for data in repeaters_data['results']]
    for repeater in repeaters:
        repeater.execute()


def main():
    run_repeaters()


if __name__ == '__main__':
    main()
