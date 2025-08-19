from pathlib import Path
import asyncio
from test_html_lib.html_tester import html_tester_singleton
import sys


async def main():
    status, errors = await html_tester_singleton.test(html_snippet)
    
    print(status)
    print("Errors:")
    for error in errors:
        print(error)

def get_file_content(file_name: str):
    with open(file_name, "r", encoding="utf-8") as file:
        return file.read()
    
command_line_args = sys.argv
if(len(command_line_args) > 1):
    file_name = command_line_args[1]
else:
    file_name = "html_snippet.html"
    
if(len(command_line_args) > 2):
    max_wait_time_seconds = int(command_line_args[2])
else:
    max_wait_time_seconds = 2
    
print(f"using file: {file_name}, to test with max wait time of {max_wait_time_seconds} seconds")

    
html_tester_singleton.max_wait_time_seconds = max_wait_time_seconds
html_snippet = get_file_content(file_name)


asyncio.run(main())







