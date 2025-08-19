
import base64
import time
import sqlparse
import requests
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire.handler import Request
from sqlparse.sql import Identifier, Statement, TokenList, Token, IdentifierList
from stopwatch import Stopwatch

#TODO: Otimizar todo o script carregando na memora do chart e da library mockada
#TODO: Mockar o fetch voltando o resultado somente com os headers.
#TODO: Style não precisa ser carregado.


# Configure Chrome options for headless mode
chrome_options = Options()
#chrome_options.add_argument("--headless")  # Run Chrome in headless mode
chrome_options.add_argument("--disable-gpu") # Recommended for headless mode on some systems
chrome_options.add_argument("--incognito")
# Initialize the WebDriver with the headless options
# If chromedriver is not in your PATH, provide the executable_path:
# driver = webdriver.Chrome(executable_path="/path/to/chromedriver", options=chrome_options)

chrome_options.add_argument("--enable-logging")
chrome_options.add_argument("--log-level=3")

chart_library_url = "https://cdn.jsdelivr.net/npm/chart.js"


def get_column_names(statement: Statement):
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

def read_url_content(url: str):
    response = requests.get(url)
    return response.text

def prepare_html_snippet(html_snippet: str, scripts: list[str]):
    html_start = "<html>"
    html_end = "</body></html>"
    html_full = ""
    html_full = html_start
    html_full += "<head>"
    for script in scripts:
        html_full += f"<script>{script}</script>"
    html_full += "<style> canvas { max-width: 300px; max-height: 300px; } </style>" 
    html_full += "</head>"
    html_full += "<div>" + html_snippet + "</div>"
    html_full += html_end
    return html_full

def test_script(driver: webdriver.Chrome):
    driver.get("https://www.envisiontecnologia.com.br")
    
    wait = WebDriverWait(driver,3) # Wait for up to 10 seconds
    wait.until(lambda driver: driver.execute_script("return document.readyState === 'complete'"))
    print("Page and JavaScript loaded successfully!")
    
    logs = driver.get_log("browser")
    print(logs)
    for log in logs:
        if(log["level"] == "SEVERE"):
            print("ERROR: ", log["message"])

def get_file_content(file_name: str):
    with open(file_name, "r", encoding="utf-8") as file:
        return file.read()
    
html_snippet = get_file_content("html_snippet.html")
dashboard_script = get_file_content("dashboard_javascript.js")
chart_library_content = read_url_content(chart_library_url)

full_html_snippet = prepare_html_snippet(html_snippet, [dashboard_script, chart_library_content])

with open("full_html_snippet.html", "w", encoding="utf-8") as file:
    file.write(full_html_snippet)

def fake_fetch_csv_response(sql: str):
    headers = get_column_names(sqlparse.parse(sql)[0])
    reponse = ""
    headers_row = []
    for header in headers:
        headers_row.append(header)
        
    reponse += ",".join(headers_row) + "\n"

    for i in range(10):
        row = [str(i)]
        for header in headers:
            row.append(str(i))
        reponse += ",".join(row) + "\n"
    return reponse

def interceptor(request: Request):
    print(request.url)
    cache_key = request.params.get("cache_key")
    if(request.url == "https://www.envisiontecnologia.com.br/"):
        request.create_response(
            status_code=200,
            headers={'Content-Type': 'text/html'},  # Optional headers dictionary
            body=full_html_snippet.encode("utf-8")
        )
    elif(request.url.find("fetchData") != -1):
        sql = request.body.decode("utf-8")
        print(f"sql: {sql}")
        print(f"sql: {get_column_names(sqlparse.parse(sql)[0])}")
        request.create_response(
            status_code=200,
            headers={'Content-Type': 'text/csv'},  # Optional headers dictionary
            body=fake_fetch_csv_response(sql).encode("utf-8")
        )

# # data_url = "data:text/html;charset=utf-8," + open("test.html", "r").read()

# SQL = "SELECT COUNT(Id) AS TotalBookings, Concat(Name, ' ', LastName) as FullName, Create, Id,  SUM(TotalFareAmountBrl) AS TotalRevenue, AVG(LengthOfStay) AS AverageStayLength FROM BI_CaixaEconomica.HotelBookings WHERE DATE(Created) >= DATE_SUB(CURRENT_DATE('America/Sao_Paulo'), INTERVAL 30 DAY)"
# SQL2 = "SELECT Id, Created, TotalFareAmountBrl as Total, Concat(Name, ' ', LastName) as FullName, LengthOfStay FROM BI_CaixaEconomica.HotelBookings WHERE DATE(Created) >= DATE_SUB(CURRENT_DATE('America/Sao_Paulo'), INTERVAL 30 DAY)"

# sqls = sqlparse.split(SQL2)
# statement = sqlparse.parse(sqls[0])[0]

timer = Stopwatch()
timer.start()
driver = webdriver.Chrome(options=chrome_options)
driver.request_interceptor = interceptor
test_script(driver)
timer.stop()

print(f"========== Elapsed miliseconds: {timer.elapsed*1000:.2f}")

time.sleep(10)

timer = Stopwatch()
timer.start()
test_script(driver)
timer.stop()
print(f"========== Elapsed miliseconds: {timer.elapsed*1000:.2f}")

time.sleep(120)

#driver.quit()
