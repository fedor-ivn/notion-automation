import os
# import custom_logging
from dotenv import load_dotenv
from notion_client import Client
import dateutil
import datetime

load_dotenv()


TIMEZONE = 'Europe/Moscow'
NOTION_API_TOKEN = os.environ['NOTION_API_TOKEN']
TASK_DATABASE_ID = os.environ['TASK_DATABASE_ID']


def main():
    # TODO: set logging
    client = Client(auth=NOTION_API_TOKEN)

    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    done_tasks = client.databases.query(
        TASK_DATABASE_ID,
        filter={
            "and": [
                {
                    "property": "Status",
                    "status": {
                        "equals": "done"
                    }
                },
                {
                    "property": "Last edited time",
                    "last_edited_time": {
                        "this_week": {}
                    }
                },
                {
                    "property": "Done",
                    "date": {
                        "is_empty": True
                    }
                }
            ]
        }
    )

    for task in done_tasks["results"]:
        client.pages.update(
            task["id"],
            properties={
                "Done": {
                    "type": "date",
                    "date": {
                            "start": current_date,
                            "end": None
                    }
                }
            }
        )

    print(done_tasks)


if __name__ == "__main__":
    main()
