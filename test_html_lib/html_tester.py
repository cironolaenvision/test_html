import asyncio
from asyncio.locks import Condition
from pathlib import Path
import time
import uuid
import sqlparse
import requests
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire.handler import Request
from sqlparse.sql import Identifier, Statement, TokenList, Token, IdentifierList

class HtmlTesterSnippet:
    html: str
    uniqueid: str
    
    def __init__(self, html: str, uniqueid: str):
        self.html = html
        self.uniqueid = uniqueid
        
class Script:
    url: str
    content: str
    lines_offset: int
    name: str
    def __init__(self, content: str, url: str, name: str):
        self.content = content
        self.url = url
        self.lines_offset = len(content.split("\n"))
        self.name = name

class HtmlTester:
    snippets_map: dict[str, HtmlTesterSnippet]
    default_chrome_options: Options
    original_chart_library_url: str =  "https://cdn.jsdelivr.net/npm/chart.js"
    dashboard_script: Script
    chart_library_script: Script
    current_snippet:str | None
    driver: webdriver.Chrome | None = None
    max_wait_time_seconds: float = 2.0
    
    def get_file_content(self, file_name: str):
        with open(file_name, "r", encoding="utf-8") as file:
            return file.read()
        
    def read_url_content(self,url: str):
        response = requests.get(url)
        return response.text
        
    def get_column_names(self,statement: Statement):
        names = []
        def parse_tokens_resursive(token):
            if(type(token) == Identifier):
                names.append(token.get_name())

            if(type(token) == IdentifierList):
                for identifier in token.get_identifiers():
                    parse_tokens_resursive(identifier)
            if(type(token) == TokenList):
                for sub_token in token.tokens:
                    parse_tokens_resursive(sub_token)
        for token in statement.tokens:
            parse_tokens_resursive(token)
        return names         
    
    def fake_fetch_csv_response(self, sql: str):
        headers = self.get_column_names(sqlparse.parse(sql)[0])
        reponse = ""
        headers_row = []
        for header in headers:
            headers_row.append(header)
            
        reponse += ",".join(headers_row) + "\n"

        for i in range(3):
            row = [str(i)]
            for header in headers:
                row.append(str(i))
            reponse += ",".join(row) + "\n"
        return reponse    

    def adjust_error_line_number(self, error_message: str) -> str:
        """
        Adjusts the line number in error messages by subtracting the lines_offset.
        Handles error messages in format like "387:17 Uncaught SyntaxError: Unexpected token ')'"
        """
        import re
        
        # Pattern to match line:column format anywhere in the error message
        # \s* allows for optional leading whitespace
        pattern = r'\s*(\d+):(\d+)'
        match = re.search(pattern, error_message)
        is_local_script = error_message.find("generated_scrit") != -1
        
        if match:
            original_line = int(match.group(1))
            if(is_local_script):
                column = match.group(2)
                
                # Adjust line number by subtracting the offset
                adjusted_line = original_line
                adjusted_line = str(adjusted_line) + " to " + str(adjusted_line + 1)
                
                # Replace the original line:column with adjusted line:column
                adjusted_error = re.sub(pattern, f'line: {adjusted_line} column: {column}', error_message)
                return adjusted_error
            else:
                return error_message
        
        return error_message

    def __init__(self, public_folder: Path, headless: bool = True, max_wait_time_seconds: int = 2) -> None:
        self.max_wait_time_seconds = max_wait_time_seconds
        self.default_chrome_options = Options()
        if(headless):
            self.default_chrome_options.add_argument("--headless")  # Run Chrome in headless mode 
        self.default_chrome_options.add_argument("--disable-gpu") # Recommended for headless mode on some systems
        self.default_chrome_options.add_argument("--incognito")
        self.default_chrome_options.add_argument("--enable-logging")
        self.default_chrome_options.add_argument("--log-level=1")
        
        self.snippets_map: dict[str, HtmlTesterSnippet] = {}
        
        self.dashboard_javascript_content = self.get_file_content(public_folder / "dashboard_javascript.js")
        self.chart_library_content = self.read_url_content(self.original_chart_library_url)
        self.dashboard_script = Script(self.dashboard_javascript_content, "dashboard_javascript.js", "dashboard_javascript")
        self.chart_library_script = Script(self.chart_library_content, "chart.js", "chart_library")
        self.html_header_content_lines = len(self.html_header_content().split("\n"))
        self.html_style_close_header_lines = len(self.html_style_close_header().split("\n"))
        self.lines_offset = self.dashboard_script.lines_offset + self.chart_library_script.lines_offset - 1 #+ 1 for the div
        
    def html_header_content(self):
        html_start = "<html><body>"
        html_start += "<head>"
        
        return html_start
    
    def html_style_close_header(self):
        html_style = "<style> canvas { max-width: 300px; max-height: 300px; } </style>" 
        html_style += "</head>"
        
        return html_style 
    
    def prepare_html_snippet(self, html_snippet: str, scripts: list[Script]):
        html_end = "</body></html>"
        html_full = self.html_header_content()
        for script in scripts:
            html_full += f"<script src=\"{script.url}\" id=\"{script.name}\"></script>"

        html_full += self.html_style_close_header()
        html_full += "<div>" + html_snippet + "</div>"
        html_full += html_end
        return html_full        
    
    def interceptor(self, request: Request):
        if(request.url.find("snippet_id") != -1):
            snippet_id = request.params.get("snippet_id")
            if(not snippet_id):
                raise Exception("no snippet_id found in the request url")
            
            snippet = self.snippets_map[snippet_id]
            if(not snippet):
                raise Exception(f"snippet with id {snippet_id} not found")
            
            full_html_snippet = self.prepare_html_snippet(
                snippet.html,
                [self.dashboard_script, self.chart_library_script]
            )
            
            with open("full_html_snippet.html", "w") as file:
                file.write(full_html_snippet)
            
            request.create_response(
                status_code=200,
                headers={'Content-Type': 'text/html'},  # Optional headers dictionary
                body=full_html_snippet.encode("utf-8")
            )
        elif(request.url.find("dashboard_javascript.js") != -1):
            request.create_response(
                status_code=200,
                headers={'Content-Type': 'text/javascript'},  # Optional headers dictionary
                body=self.dashboard_script.content.encode("utf-8")
            )
        elif(request.url.find("chart.js") != -1):
            request.create_response(
                status_code=200,
                headers={'Content-Type': 'text/javascript'},  # Optional headers dictionary
                body=self.chart_library_script.content.encode("utf-8")
            )
        elif(request.url.find("fetchData") != -1):
            sql = request.body.decode("utf-8")
            request.create_response(
                status_code=200,
                headers={'Content-Type': 'text/csv'},  # Optional headers dictionary
                body=self.fake_fetch_csv_response(sql).encode("utf-8")
            )
            
        else:
            request.create_response(
                status_code=200,
                body="".encode()
            )
    
    async def test(self, html: str) -> [bool, list[str]]:
        self.current_snippet = html
        uniqueid = str(uuid.uuid4())
        
        self.snippets_map[uniqueid] = HtmlTesterSnippet(html, uniqueid)
        
        base_url = "http://localhost:8080"
        full_url = f"{base_url}/?snippet_id={uniqueid}"

        
        try:
            success = True
            errors:list[str] = []        
            
            self.driver = webdriver.Chrome(options=self.default_chrome_options)
            self.driver.request_interceptor = self.interceptor
            self.driver.get(full_url)
            wait = WebDriverWait(self.driver,10) # Wait for up to 10 seconds        
            wait.until(lambda driver: driver.execute_script("return document.readyState === 'complete'"))

            attempts = 0
            total_wait_time = self.max_wait_time_seconds
            split = total_wait_time/20
            while(len(errors) == 0 and attempts*split < total_wait_time): #about total_wait_time seconds
                logs = self.driver.get_log("browser")
                for log in logs:
                    if(log["level"] == "SEVERE" or log["level"] == "ERROR"):
                        success = False
                        
                        message = log["message"]
                        
                        is_from_local_script = message.find(full_url) != -1
                        
                        error_message = log["message"].replace(full_url, "generated_scrit: ")
                        error_message = error_message.replace(base_url, "").strip()
                        error_message = self.adjust_error_line_number(error_message) if is_from_local_script else error_message

                        # Adjust the line number in the error message
                        errors.append(error_message)
                attempts += 1
                await asyncio.sleep(split)
                
        finally:
            if(self.driver):
                self.driver.quit()
                
        return success, errors

        
html_tester_singleton = HtmlTester(Path(".")) #users should use only this instance
