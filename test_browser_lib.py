from pathlib import Path
import asyncio
from test_html_lib.html_tester import html_tester_singleton as tester
import sys


async def main():
    status, errors = await tester.test(html_snippet)
    
    print(status)
    print("Errors:")
    for error in errors:
        print(error)

def get_file_content(file_name: str):
    with open(file_name, "r", encoding="utf-8") as file:
        return file.read()
    
command_line_args = sys.argv
file_name = command_line_args[1]


html_snippet = get_file_content(file_name)


asyncio.run(main())







