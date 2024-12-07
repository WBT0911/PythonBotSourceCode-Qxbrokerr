import os
import re
import csv
import sys
import glob
import json
import time
import pycurl
import random
import asyncio
import certifi
import colorama
import urllib.parse
from io import BytesIO
from termcolor import colored
from datetime import datetime, timedelta
from strategies import strategy
from playwright.async_api import async_playwright
from playwright._impl._errors import TargetClosedError
#command> pip install pycurl certifi colorama termcolor playwright
#command> playwright install

# Initialize colorama for Windows
colorama.init()

# Constants
ARGS = sys.argv[1:]
CACHE_DIR = './cache/'
CONFIG_DIR = './config/'
COOKIE_DIR = './cookies/'
RESULT_DIR = './results/'

# clear the console
def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

# Set window size
def set_window_size(columns, rows):
    #clear_console()
    cmd = f'mode con: cols={columns} lines={rows}' if os.name == 'nt' else f'printf "\\033[8;{rows};{columns}t"'
    os.system(cmd)

set_window_size(128, 9999)

# Ensure the folders exist
for dir_path in [CACHE_DIR, CONFIG_DIR, COOKIE_DIR, RESULT_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Get sign
def get_sign(num):
    return 'negative' if num < 0 else 'zero' if num == 0 else 'positive'

# Function to get string between
def gstrb(from_str, to_str, strs, offset=0):
    offset_start = (strs.find(from_str, offset) + len(from_str)) if (offset_start := strs.find(from_str, offset)) != -1 else offset
    offset_end = strs.find(to_str, offset_start) if (offset_end := strs.find(to_str, offset_start)) != -1 else len(strs)
    return strs[offset_start:offset_end]

# Tries to read the file `filename` and return its content, or None if file doesn't exist.
def file_get_contents(filename):
    try: return open(filename, 'r', newline='', encoding='utf-8').read()
    except FileNotFoundError: return ''
# Tries to write `content` to `filename` and returns True if successful, False otherwise.
def file_put_contents(filename, content, mode='w'):
    try: open(filename, mode, newline='', encoding='utf-8').write(content); return len (content)
    except IOError: return False

# Format line as CSV and write to file pointer
def fputcsv(file_stream, fields, separator=',', enclosure='"', escape='\\', eol='\n'):
    writer = csv.writer(file_stream, delimiter=separator, quotechar=enclosure, escapechar=escape, lineterminator=eol, quoting=csv.QUOTE_MINIMAL)
    return writer.writerow(fields)
# Gets line from file pointer and parse for CSV fields
def fgetcsv(file_stream, length=None, separator=',', enclosure='"', escape='\\'):
    content = file_stream.read(length) if length else None
    reader = csv.reader(StringIO(content) if content else file_stream, delimiter=separator, quotechar=enclosure, escapechar=escape)
    try:
        return next(reader)
    except StopIteration:
        return False

# Parses Netscape cookie file content to a dict; joins as string if specified.
def loads_cookie(content, join=False):
    cookies = {
        line.split('\t')[5]: line.split('\t')[6]
        for line in content.splitlines()
        if line.strip() and not (line.startswith('#') and not line.startswith('#HttpOnly'))
    }
    return '&'.join([f'{key}={value}' for key, value in cookies.items()]) if join else cookies

# Builds a list of cookies with specified expiration time for a given URL
def build_cookie(cookies, url, expiration_time=86400):
    expiration_date = (datetime.now() + timedelta(seconds=expiration_time)).timestamp()
    return [
        {'name': name, 'value': value, 'url': url, 'expires': expiration_date}
        for name, value in cookies.items()
    ]

# Reads the proxy list from a file and strips each line
def loads_proxy(filename):
    # Ensure the proxy file exists, and if not, create it with empty content
    if not os.path.exists(filename):
        file_put_contents(filename, '')

    content = file_get_contents(filename).strip ()
    proxy_list = content.splitlines()
    return list(map(lambda x: x.strip(), proxy_list))

# Class to manage and rotate an array
class Rotator:
    def __init__(self, arr):
        self.arr = arr or [""]  # Use arr if not empty, otherwise [""]
        self.current_position = 0
    
    def rotate_left(self):
        self.current_position = (self.current_position - 1) % len(self.arr)
    
    def rotate_right(self):
        self.current_position = (self.current_position + 1) % len(self.arr)
    
    def get_next(self):
        value = self.arr[self.current_position]
        self.rotate_right()
        return value
    
    def get_prev(self):
        self.rotate_left()
        value = self.arr[self.current_position]
        return value

# Function to validate email format
def validate_email(email):
    if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        return True
    return False
# Function to validate 6-digit PIN-code
def validate_pin_code(pincode):
    if re.match(r'^\d{6}$', pincode):
        return True
    return False

# Format number
def format_number(value, decimal_places=2):
    if isinstance(value, float):
        return round(value, decimal_places)
    elif isinstance(value, int):
        return value

# Format time
def format_time(strtime):
    match = re.fullmatch(r'(\d+)(sec|min|h|d)', strtime)
    if match:
        value, unit = match.groups()
        value = int(value)
        return value if unit == 'sec' else value * 60 if unit == 'min' else value * 3600 if unit == 'h' else value * 86400
    return 0

# Format strtime
def format_strtime(time, suff={}):
    h, remainder = divmod(time, 3600)
    m, s = divmod(remainder, 60)
    return ' '.join(f"{val}{unit}" for val, unit in ((h, suff.get('h', 'H')), (m, suff.get('m', 'M')), (s, suff.get('s', 'sec'))) if val)

# Returns the next rounded timestamp after adding the specified seconds.
def get_time_next(seconds):
    ft = int(time.time()) + seconds
    left = ft % 60
    return ft - left if left < 30 else ft + (60 - left)

def strip_ansi(text):
    # Strip ANSI color codes from a string
    return re.sub(r'\x1B[@-_][0-?]*[ -/]*[@-~]', '', text)

# Pretty Table Print
class PrettyTablePrint:
    def __init__(self, header):
        self.header = header
        self.column_widths = [0] * len(header)

    def strip_ansi(self, text):
        # Strip ANSI color codes from a string
        return re.sub(r'\x1B[@-_][0-?]*[ -/]*[@-~]', '', text)

    def get_column_widths(self, rows):
        # Calculate the maximum width of each column based on the header and rows
        self.column_widths = [len(self.strip_ansi(field)) for field in self.header]
        for row in rows:
            for i, cell in enumerate(row):
                cell_length = len(self.strip_ansi(str(cell)))
                self.column_widths[i] = max(self.column_widths[i], cell_length)
        return self.column_widths

    def print_separator(self):
        # Print a row separator
        separator = '+'.join(['-' * (w + 2) for w in self.column_widths])
        print(f"+{separator}+")

    def print_header(self):
        # Create the header row and separator
        self.print_separator()
        header_row = "| " + " | ".join([field.center(width) for field, width in zip(self.header, self.column_widths)]) + " |"
        print(header_row)
        self.print_separator()

    def print_row(self, row):
        # Format and print a single row
        if len(row) != len(self.header):
            raise ValueError("Row length does not match header length.")
        
        formatted_cells = []
        for cell, width in zip(row, self.column_widths):
            cell_text = str(cell)
            cell_length = len(self.strip_ansi(cell_text))
            padding = width - cell_length
            left_padding = padding // 2
            right_padding = padding - left_padding
            formatted_cell = ' ' * left_padding + cell_text + ' ' * right_padding
            formatted_cells.append(formatted_cell)
        
        formatted_row = "| " + " | ".join(formatted_cells) + " |"
        print(formatted_row)

    def print_footer(self):
        # Print the table footer
        self.print_separator()

# Function to setup PyCURL
def curl_setup(params):
    c = pycurl.Curl()
    c.setopt(c.SSL_VERIFYHOST, 2)
    c.setopt(c.SSL_VERIFYPEER, 0)
    c.setopt(c.URL, params.get('url'))
    c.setopt(c.CAINFO, certifi.where())
    c.setopt(c.PROXY, params.get('proxy', ''))
    c.setopt(c.WRITEDATA, params.get('buffer'))
    c.setopt(c.ACCEPT_ENCODING, 'gzip, deflate')
    c.setopt(c.HTTPHEADER, params.get('headers', []))
    cookie_file = f"{COOKIE_DIR}{gstrb('//', '/', params.get('url'))}.txt"
    c.setopt(c.COOKIEJAR, cookie_file)
    c.setopt(c.COOKIEFILE, cookie_file)
    if params.get('postfields'):
        c.setopt(c.POSTFIELDS, params.get('postfields'))
    return c

# Common headers generator with overwrite capability
def curl_headers(custom_headers={}):
    default_headers = {
        'User-Agent': custom_headers.get('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko'),
        'Accept': custom_headers.get('Accept', '*/*'),
        'Accept-Language': custom_headers.get('Accept-Language', 'en-US,en;q=0.5'),
        'Upgrade-Insecure-Requests': custom_headers.get('Upgrade-Insecure-Requests', '1'),
        'Sec-Fetch-Dest': custom_headers.get('Sec-Fetch-Dest', 'document'),
        'Sec-Fetch-Mode': custom_headers.get('Sec-Fetch-Mode', 'navigate'),
        'Sec-Fetch-Site': custom_headers.get('Sec-Fetch-Site', 'same-origin'),
        'Sec-Fetch-User': custom_headers.get('Sec-Fetch-User', '?1'),
        'Priority': custom_headers.get('Priority', 'u=1')
    }

    for key, value in custom_headers.items():
        if key not in default_headers:
            default_headers[key] = value

    return [f'{key}: {value}' for key, value in default_headers.items()]

# Function to perform login using PyCURL
async def login(email='', password='', token='', code='', proxy=''):
    buffer = BytesIO()

    body = {
        '_token': token,
        'email': email,
        'password': password,
        'remember': '1'
    }
    if code:
        body['keep_code'] = '1'
        body['code'] = code

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    }
    if token:
        headers['Content-Type'] = 'application/x-www-form-urlencoded'

    params = {
        'url': 'https://qxbroker.com/en/sign-in/',
        'proxy': proxy,
        'buffer': buffer,
        'headers': curl_headers(headers),
    }
    if token:
        params['postfields'] = urllib.parse.urlencode(body)

    c = curl_setup(params)

    try:
        c.perform()
    except pycurl.error as e:
        return f'Error: {e}'
    finally:
        c.close()

    return buffer.getvalue().decode('utf-8')

# Function to fetch data using PyCURL
async def get_data(url, proxy=''):
    buffer = BytesIO()
    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    params = {
        'url': url,
        'proxy': proxy,
        'buffer': buffer,
        'headers': curl_headers(headers)
    }
    c = curl_setup(params)

    try:
        c.perform()
    except pycurl.error as e:
        return f'Error: {e}'
    finally:
        c.close()

    return buffer.getvalue().decode('utf-8')

# Function to fetch user info using PyCURL
async def get_user_info(proxy=''):
    return await get_data ('https://qxbroker.com/api/v1/cabinets/digest', proxy)

# Function to fetch trades history using PyCURL
async def get_trades_history(account_type, proxy=''):
    return await get_data (f'https://qxbroker.com/api/v1/cabinets/trades/history/type/{account_type}?page=1', proxy)

# Function to fetch pending trades using PyCURL
async def get_pending_trades(account_type, proxy=''):
    return await get_data (f"https://qxbroker.com/api/v1/trades/pending?is_demo={['live', 'demo'].index(account_type)}&page=1", proxy)

# Rebuilds the instruments dictionary, grouping by 'real' or 'otc' and then by the key at index 3.
# Each group is sorted by index 14 (bool) and index 18, prioritizing True and then max value at index 18.
# The result is sorted by the maximum value of index 18 in each group.
def rebuild_instruments(data):
    result = {'real': {}, 'otc': {}}
    
    for item in data:
        key1 = 'real' if item[11] == 0 else 'otc'
        key2 = item[3]
        if key2 not in result[key1]:
            result[key1][key2] = []
        result[key1][key2].append(item)
    
    # Sort each group by index 14 (bool) and index 18
    for key1 in result:
        for key2 in result[key1]:
            result[key1][key2].sort(key=lambda x: (x[14], x[18]), reverse=True)
    
    # Sort each category by the maximum value of index 18 in each group
    result['otc'] = dict(sorted(result['otc'].items(), key=lambda x: x[1][0][18], reverse=True))
    result['real'] = dict(sorted(result['real'].items(), key=lambda x: x[1][0][18], reverse=True))
    
    # Sort result categories 'otc' and 'real' by the maximum value of index 18
    #result = dict(sorted(result.items(), key=lambda x: next(iter(x[1].values()))[0][18], reverse=True))
    result = dict(sorted(result.items(), key=lambda x: x[1][list(x[1].keys())[0]][0][18], reverse=True))

    return result

# Stats Result
def calculate_stats(rows):
    unique_assets, total_amount = set(), 0
    counts = {'call': 0, 'put': 0, 'win': 0, 'loss': 0, 'refund': 0}
    
    for row in rows:
        #row = [strip_ansi(value) if isinstance(value, str) else value for value in row]
        unique_assets.add(row[1])
        try:
            total_amount += row[3]
        except ValueError:
            continue
        if row[5] in counts:
            counts[row[5]] += 1
        if row[6] in counts:
            counts[row[6]] += 1

    average_return = (row[9]*100)/total_amount if total_amount else 0

    return {
        "Total Round": rows[-1][0],
        "Asset": len(unique_assets),
        "Action Call": counts['call'],
        "Action Put": counts['put'],
        "Total Win": counts['win'],
        "Total Loss": counts['loss'],
        "Total Refund": counts['refund'],
        "ACCURACY%": f"{(counts['win']/(counts['win']+counts['loss']))*100}%"
    }

# Function strategies
def strategies(user_input={}, instruments_list={}, trade_data={}):

    # Get market type and financial instruments
    market_type = user_input.get('market_type', 'all')
    financial_instruments = user_input.get('financial_instruments', 'all')
    market_type = next(iter(instruments_list)) if market_type == 'all' else market_type
    financial_instruments = next(iter(instruments_list[market_type])) if financial_instruments == 'all' else financial_instruments

    asset_info = instruments_list[market_type][financial_instruments][0]
    asset, asset_return, asset_is_active = asset_info[1], asset_info[18], asset_info[14]

    # Return False if asset is not active or minimum return% not match or an open orders is waiting
    if not asset_is_active or user_input['minimum_return'] > asset_return or trade_data['result'] == '??':
        return False

    trade_option = strategy (user_input, instruments_list, trade_data)
    #random.choice(['call', 'put']) if user_input['trade_option'] == 'random' else user_input['trade_option']

    is_demo = {'demo':1, 'live':0}[user_input['account_type']]
    bet_level = user_input['bet_level'] - 1

    # Adjust step based on trade result
    if trade_data['result'] == {'martingale':'win','compounding':'loss'}[user_input['trading_type']] or bet_level <= trade_data['step'] and trade_data['result'] in ['win','loss']:
        trade_data['step'] = 0
    elif trade_data['result'] == {'martingale':'loss','compounding':'win'}[user_input['trading_type']]:
        trade_data['step'] += 1

    # Update profit based on the result of the previous trade
    if trade_data.get('orders/open', False) and trade_data['result'] in ['win','loss']:
        trade_data['profit'] += trade_data['closed_order']['profit']

    new_order = {
        "orders/open": {
            "asset": asset,
            "amount": user_input['bet_amounts'][trade_data['step']],
            "time": user_input['trade_time'] if user_input['time_option'] == 100 else get_time_next(user_input['trade_time']),
            "action": trade_option,
            "isDemo": is_demo,
            "tournamentId": 0,
            "requestId": int(time.time())+7,
            "optionType": user_input['time_option']
        },
        "step": trade_data['step'],
        "result": '??',
        "profit": trade_data['profit'],
    }

    # Save new order to cache file
    file_put_contents(f'{CACHE_DIR}new_order.json', json.dumps(new_order))

    # Retrieve and update the last orders
    rows = json.loads(file_get_contents(f'{CACHE_DIR}orders.json').strip() or '[]')

    if trade_data.get('orders/open', False):
        row = [
            len(rows)+1,
            trade_data['orders/open']['asset'],
            trade_data['closed_order']['percentProfit'],#{'win':trade_data['closed_order']['percentProfit'],'refund':0,'loss':-100}[trade_data['result']],
            trade_data['orders/open']['amount'],
            format_strtime(user_input['trade_time']),
            trade_data['orders/open']['action'],
            trade_data['result'],
            format_number(trade_data['accountBalance']),
            format_number(trade_data['closed_order']['profit']),
            format_number(trade_data['profit']),
        ]
        rows.append(row)

    # Save updated orders to cache file
    file_put_contents(f'{CACHE_DIR}orders.json', json.dumps(rows))

    header = ['No', 'Asset', 'Return%', 'Amount', 'Time', 'Action', 'Result', 'accountBalance', 'Profit', 'TotalProfit']
    # Initialize PrettyTablePrint with header
    printer = PrettyTablePrint(header)
    # Calculate column widths based on rows
    #printer.column_widths = printer.get_column_widths(rows)
    # Set column widths
    printer.column_widths = [7, 17, 7, 7, 7, 7, 7, 15, 7, 15]

    # Print header if it's the first print; otherwise, print the row
    if trade_data.get('orders/open', False):
        row[1] = colored(row[1], {'real':'blue','otc':'cyan'}[market_type])
        row[2] = f'{row[2]}%'#row[2] = colored(f'{row[2]}%', {'positive':'green','zero':'yellow','negative':'red'}[get_sign(row[2])])
        row[5] = colored(row[5], {'call':'green','put':'red'}[row[5]])
        row[6] = colored(row[6], {'win':'green','refund':'yellow','loss':'red'}[row[6]])
        #row[8] = colored(row[8], {'positive':'green','zero':'yellow','negative':'red'}[get_sign(row[8])])
        row[9] = colored(row[9], {'positive':'green','zero':'yellow','negative':'red'}[get_sign(row[9])])
        printer.print_row(row)
    else:
        printer.print_header()

    # Print message and exit if targets are reached
    if user_input['profit_target'] <= trade_data['profit'] or trade_data['profit'] <= -user_input['loss_target']:
        # Print the footer
        printer.print_footer()
        # Determine if the profit is positive or not
        isProfit = trade_data['profit'] > 0
        # Determine color and message based on profit
        color = 'green' if isProfit else 'red'
        message = "Profit target reached!" if isProfit else "Loss target reached!"
        print(colored(message, color))
        stats = calculate_stats(json.loads(file_get_contents(f'{CACHE_DIR}orders.json').strip() or '[]'))
        for key, value in stats.items():
            print(f"{key}: {value}")
        return ['window.close', True]

    return ['orders/open', new_order['orders/open']]

# Function to handle message from WebSocket
async def handle_message(window, event, message):
    d_arrow = colored('↓', 'red')
    u_arrow = colored('↑', 'green')
    new_order_file = f'{CACHE_DIR}new_order.json'

    if event == '↓':
        #print(f"[Socket:] => {d_arrow}: {message}")

        if all(s in message for s in ['"deals":[{"id":"', '"openTime":"', '"closeTime":"', '"profit":', '"percentProfit":', '"percentLoss":', '"closeMs":']):
            closed_order = json.loads('{' + gstrb ('{', '#ENDLINE', message))
            trade_data = json.loads(file_get_contents(new_order_file).strip() or '{"step": 0, "result": "?", "profit": 0}')
            if closed_order['deals'][0]['id'] == trade_data['opened_order']['id']:
                trade_data['closed_order'] = closed_order['deals'][0]
                trade_data['accountBalance'] += trade_data['closed_order']['profit']
                trade_data['result'] = 'win' if trade_data['closed_order']['profit'] > 0 else 'loss' if trade_data['closed_order']['profit'] < 0 else 'refund'
                file_put_contents(new_order_file, json.dumps(trade_data))
                user_input = json.loads(file_get_contents (f'{CONFIG_DIR}user_input.json'))
                instruments_list = json.loads(file_get_contents (f'{CONFIG_DIR}instruments_list.json'))
                open_order = strategies(user_input, instruments_list, trade_data)
                if open_order and open_order[0] == 'orders/open':
                    return ['orders/open', json.dumps(open_order, separators=(',', ':'))]
                elif open_order and open_order[0] == 'window.close':
                    await window.close()
                else:
                    return ['console.log', f'Message received and handled: {message}']
        elif all(s in message for s in ['"id":"', '"openTime":"', '"closeTime":"', '"profit":', '"percentProfit":', '"percentLoss":', '"accountBalance":', '"requestId":']):
            opened_order = json.loads('{' + gstrb ('{', '#ENDLINE', message))
            trade_data = json.loads(file_get_contents(new_order_file).strip() or '{"step": 0, "result": "?", "profit": 0}')
            if opened_order['requestId'] == trade_data['orders/open']['requestId']:
                trade_data['accountBalance'] = opened_order['accountBalance']
                trade_data['opened_order'] = opened_order
                file_put_contents(new_order_file, json.dumps(trade_data))
        elif ',"AUDCAD","AUD/CAD","currency",' in message and ',"XAUUSD_otc","Gold (OTC)","commodity",' in message:
            instruments_list = '[' + gstrb ('[', '#ENDLINE', message)
            instruments_list = rebuild_instruments(json.loads(instruments_list))
            file_put_contents (f'{CONFIG_DIR}instruments_list.json', json.dumps(instruments_list))
            user_input = json.loads(file_get_contents (f'{CONFIG_DIR}user_input.json'))
            trade_data = json.loads(file_get_contents(new_order_file).strip() or '{"step": 0, "result": "?", "profit": 0}')
            open_order = strategies(user_input, instruments_list, trade_data)
            if open_order and open_order[0] == 'orders/open':
                return ['orders/open', json.dumps(open_order, separators=(',', ':'))]
            elif open_order and open_order[0] == 'window.close':
                await window.close()
            else:
                return ['console.log', f'Message received and handled: {message}']
        #elif not isinstance(message, str):
            #sys.exit(0)

    elif event == '↑':
        #print(f"[Socket:] => {int(time.time())} - {u_arrow}: {message}")
        return ['console.log', f'Message received and handled: {message}']

async def run_browser_script(user_input):
    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-infobars',
                '--disable-extensions',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled'
            ]
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )

        trade_page = await context.new_page()

        url = {'live': 'https://qxbroker.com/en/trade', 'demo': 'https://qxbroker.com/en/demo-trade'}[user_input['account_type']]
        urlcookie1 = 'https://qxbroker.com/'
        urlcookie2 = 'https://ws2.qxbroker.com/'

        # Function to delete a specific HTTP-only cookie by name
        async def delete_specific_cookie(context, cookie_name):
            try:
                cookies = await context.cookies()
                for cookie in cookies:
                    if cookie.get('name') == cookie_name:
                        await context.clear_cookies(
                            name=cookie_name,
                            domain=cookie['domain'],
                            path=cookie['path']
                        )
                        #print(f"Cookie '{cookie_name}' deleted")
                        return
                #print(f"Cookie '{cookie_name}' not found")
            except TargetClosedError:
                print("Context or page is closed, cannot delete cookie.")
            except Exception as e:
                print(f"Error deleting cookie: {e}")

        # Function to run the deletion periodically
        async def periodic_cookie_deletion(context, cookie_name, interval):
            while True:
                try:
                    await delete_specific_cookie(context, cookie_name)
                except TargetClosedError:
                    print("Context or page is closed, exiting the loop.")
                    break
                except Exception as e:
                    print(f"Exception during periodic deletion: {e}")
                    break
                await asyncio.sleep(interval)

        try:
            # Expose the handle_message function to JavaScript
            await trade_page.expose_function('notifyBackend', lambda event, message: handle_message(trade_page, event, message))

            # Inject cookies before opening the page
            await trade_page.context.add_cookies(build_cookie(loads_cookie(file_get_contents(f"{COOKIE_DIR}{gstrb('//', '/', url)}.txt")), urlcookie1))
            await trade_page.context.add_cookies(build_cookie(loads_cookie(file_get_contents(f"{COOKIE_DIR}{gstrb('//', '/', url)}.txt")), urlcookie2))

            # Inject the JavaScript WebSocket Hook script before the page's own scripts run
            await trade_page.add_init_script(file_get_contents('bypass.js')+file_get_contents('wsHook.js'))

            # Open a webpage
            await trade_page.goto(url, timeout=60000)

            # Start the periodic deletion in the background
            cookie_task = asyncio.create_task(periodic_cookie_deletion(trade_page.context, 'cf_clearance', 5))

            # Wait for the page to fully load
            await trade_page.wait_for_load_state('load')

            # Inject another script
            #await trade_page.evaluate(file_get_contents('bypass.js')+file_get_contents('wsHook.js'))

            # Wait for the page to close
            await trade_page.wait_for_event('close', timeout=0)
            # Cancel the indefinite task
            cookie_task.cancel()
            # Keep the browser open indefinitely
            #await asyncio.Future()  # Run forever
        except TargetClosedError:
            print("Context or page is closed, exiting")
        except Exception as e:
            print(f"Exception during periodic deletion: {e}")
        finally:
            pass

# Function to print a formatted welcome message with a decorative border
def print_welcome_message(border_length=77):
    border_line = colored('*' * border_length, 'cyan')
    empty_line = colored('*' + ' ' * (border_length - 2) + '*', 'cyan')
    
    welcome_text = colored('Welcome to ', 'white') + colored('Auto Trading Bot', 'green')
    contact_text = colored('Contact us on ', 'white') + colored('Telegram', 'magenta') + colored(' to implement any strategy on your bot', 'white')

    # Calculate the spaces needed on each side of the centered text
    welcome_spaces = (border_length - 2 - len('Welcome to Auto Trading Bot')) // 2
    contact_spaces = (border_length - 2 - len('Contact us on Telegram to implement any strategy on your bot')) // 2

    # Create welcome and contact lines with proper spacing
    welcome_line = colored('*', 'cyan') + ' ' * welcome_spaces + welcome_text + ' ' * welcome_spaces + colored('*', 'cyan')
    contact_line = colored('*', 'cyan') + ' ' * contact_spaces + contact_text + ' ' * contact_spaces + colored(' *', 'cyan')

    print(border_line)
    print(empty_line)
    print(welcome_line)
    print(empty_line)
    print(contact_line)
    print(empty_line)
    print(border_line)

# Function to print a formatted user_info message
def print_user_info_message(user_info):
    print('\nWelcome back!')
    print('User: ' + colored(user_info['data']['email'], 'blue'))
    print('Country: ' + colored(user_info['data']['countryName'], 'blue'))
    print('Token: ' + colored(user_info['data']['token'], 'blue'))
    print('LiveBalance: ' + colored(user_info['data']['liveBalance'], 'green'))
    print('DemoBalance: ' + colored(user_info['data']['demoBalance'], 'cyan'))

# Main asynchronous function to orchestrate the entire process
async def main():

    # Remove all JSON files from the cache directory
    [os.remove(f) for f in glob.glob(f'{CACHE_DIR}*.json')]

    print_welcome_message()

    while True:

        logged = False

        # Get user info
        user_info = await get_user_info()

        if '{"data":{"' in user_info:
            user_info = json.loads(user_info)
            print('Previous session detected!')
            print('User: ' + colored(user_info['data']['email'], 'blue'))

            while True:
                print('\n1 - Resume and skip login')
                print('2 - Drop and connect a new account')
                # Prompt for resume
                resume = input('Enter your choice: ')
                if resume == '1':
                    print_user_info_message(user_info)
                    logged = True
                    break # Exit the loop on valid selection
                elif resume == '2':
                    print(colored('Dropping previous session...', 'yellow'))
                    [os.remove(f) for f in glob.glob(f'{COOKIE_DIR}*qxbroker.com.txt')]
                    user_info = '{"message":"Unauthenticated."}'
                    break # Exit the loop on valid selection
                else:
                    print(colored('Invalid choice. Please select 1 or 2.', 'yellow'))

        if not logged and '{"message":"Unauthenticated."}' in user_info:
            while True:
                # Prompt for email
                email = input('Enter your email: ')
                if validate_email(email):
                    break # Exit the loop on valid selection
                else:
                    print(colored('Invalid email format.', 'yellow'))
            # Prompt for password
            password = input('Enter your password: ')

            # Attempt login
            sign_in_page = await login()

            if '<input type="hidden" name="_token" value="' in sign_in_page:
                token = gstrb ('<input type="hidden" name="_token" value="', '"', sign_in_page)
                sign_in_page = await login(email, password, token)

                if "Please enter the PIN-code we've just sent to your email" in sign_in_page:
                    token = gstrb ('<input type="hidden" name="_token" value="', '"', sign_in_page)
                    while True:
                        # Prompt for PIN-code
                        code = input("Please enter the PIN-code we've just sent to your email: ")
                        if validate_pin_code(code):
                            break # Exit the loop on valid selection
                        else:
                            print(colored('Invalid 6-digit code.\nPlease enter a valid 6-digit code.', 'yellow'))
                    sign_in_page = await login(email, password, token, code)

            # Get user info
            user_info = await get_user_info()
            if '{"data":{"' in user_info:
                user_info = json.loads(user_info)
                print_user_info_message(user_info)
                logged = True

        if logged:
            # Login successful, proceed to account selection
            # Prompt for account type
            while True:
                print('\nD - Demo Account')
                print('L - Live Account')
                account_type = input('Select Account Type: ')
                if account_type.upper() == 'D':
                    account_type = 'demo'
                    print(colored(f'You selected {account_type} account.', 'cyan'))
                    break # Exit the loop on valid selection
                elif account_type.upper() == 'L':
                    account_type = 'live'
                    print(colored(f'You selected {account_type} account.', 'green'))
                    break # Exit the loop on valid selection
                else:
                    print(colored('Invalid account type. Please select D or L.', 'yellow'))

            # Get trades history
            trades_history = await get_trades_history(account_type, proxy='')

            # Prompt for trading type
            while True:
                print('\n1 - Compounding')
                print('2 - Martingale')
                trading_type = input('Select your trading type: ')
                if trading_type == '1':
                    trading_type = 'compounding'
                    print(colored(f'You selected {trading_type.title()}', 'blue'))
                    break # Exit the loop on valid selection
                elif trading_type == '2':
                    trading_type = 'martingale'
                    print(colored(f'You selected {trading_type.title()}', 'blue'))
                    break # Exit the loop on valid selection
                else:
                    print(colored('Invalid selection. Please select 1 or 2', 'yellow'))

            # Prompt for bet levels
            while True:
                bet_level = input('Enter your maximum step level for the bet amount: ')
                if bet_level.isdigit() and int(bet_level) >= 1:
                    bet_level = int(bet_level)
                    break  # Exit the loop on valid input
                else:
                    print(colored('Invalid input. Please enter a numeric value >=1 .', 'yellow'))
            
            bet_amounts = []
            for index in range(bet_level):
                # Prompt for bet amounts
                while True:
                    bet_amount = input(f'STEP {index + 1} AMOUNT: ')
                    if bet_amount.isdigit() and int(bet_amount) >= 1:
                        bet_amounts.append(int(bet_amount))
                        break  # Exit the loop on valid input
                    else:
                        print(colored('Invalid input. Please enter a numeric value >=1 .', 'yellow'))
            # Process the collected bet amounts as needed
            print(colored(f'Collected bet amounts: {bet_amounts}', 'blue'))

            # Prompt for Financial Instruments
            instrument_items = ['currency', 'cryptocurrency', 'commodity', 'stock', 'all']
            while True:
                # Print the items
                print('\nSelect your Financial Instruments:')
                for index, value in enumerate(instrument_items, start=1):
                    print(f'{index} - {value.title()}')
                financial_instruments = input('Enter the number corresponding to your choice: ')
                financial_instruments = int(financial_instruments)-1 if financial_instruments.isdigit() else -1
                if 0 <= financial_instruments < len(instrument_items):
                    financial_instruments = instrument_items[financial_instruments].lower()
                    print(colored(f'You selected {financial_instruments.title()}', 'blue'))
                    break # Exit the loop on valid selection
                else:
                    print(colored(f'Invalid selection. Please select a number from 1 to {len(instrument_items)}', 'yellow'))

            # Prompt for Market Type
            market_items = ['otc', 'real', 'all']
            while True:
                # Print the items
                print('\nSelect your Market Type:')
                for index, value in enumerate(market_items, start=1):
                    print(f'{index} - {value.title()}')
                market_type = input('Enter the number corresponding to your choice: ')
                market_type = int(market_type)-1 if market_type.isdigit() else -1
                if 0 <= market_type < len(market_items):
                    market_type = market_items[market_type].lower()
                    print(colored(f'You selected {market_type.title()}', 'blue'))
                    break # Exit the loop on valid selection
                else:
                    print(colored(f'Invalid selection. Please select a number from 1 to {len(market_items)}', 'yellow'))

            # Prompt for Time Options
            time_options = [['fixed',100], ['clock',1]]
            while True:
                # Print the items
                print('\nSelect your Time Option:')
                for index, value in enumerate(time_options, start=1):
                    print(f'{index} - {value[0].title()} TIME')
                time_option = input('Enter the number corresponding to your choice: ') if market_type == 'otc' else '2'
                time_option = int(time_option)-1 if time_option.isdigit() else -1
                if 0 <= time_option < len(time_options):
                    print(colored(f'You selected {time_options[time_option][0].title()} TIME', 'blue'))
                    time_option = time_options[time_option][1]
                    break # Exit the loop on valid selection
                else:
                    print(colored(f'Invalid selection. Please select a number from 1 to {len(time_options)}', 'yellow'))

            # Prompt for Trade Time
            while True:
                min_time = {100:5, 1:60}[time_option]
                max_time = 14400
                print('\nMinimum: ' + colored(format_strtime(min_time, {'m':'min'}), 'blue'))
                print('Maximum: ' + colored('240min', 'yellow'))
                trade_time = input('Enter your trade time: ')
                trade_time = int(trade_time)*60 if trade_time.isdigit() else format_time(trade_time.lower())
                if min_time <= trade_time <= max_time:
                    print(colored(f"You selected {format_strtime(trade_time, {'m': 'min'})}", 'blue'))
                    break # Exit the loop on valid selection
                else:
                    print(colored(f"Invalid trade time. Please select a time from {format_strtime(min_time, {'m': 'min'})} to 240min", 'yellow'))

            # Prompt for Minimum Return
            while True:
                print('\nMinimum: ' + colored('20', 'blue'))
                print('Maximum: ' + colored('100', 'yellow'))
                minimum_return = input('Enter your minimum return %: ')
                minimum_return = int(minimum_return) if minimum_return.isdigit() else 0
                if 20 <= minimum_return <= 100:
                    break # Exit the loop on valid selection
                else:
                    print(colored('Invalid minimum return %. Please select a number from 20 to 100', 'yellow'))

            # Prompt for trade option
            option_items = [['call','green'], ['put','red'], ['random','yellow']]
            while False:
                # Print the items
                print('\nSelect your trade option:')
                for index, value in enumerate(option_items, start=1):
                    print(f'{index} - ' + colored(f'{value[0].title()}', value[1]))
                trade_option = input('Enter the number corresponding to your choice: ')
                trade_option = int(trade_option)-1 if trade_option.isdigit() else -1
                if 0 <= trade_option < len(option_items):
                    print('You selected ' + colored(f'{option_items[trade_option][0].title()}', option_items[trade_option][1]))
                    trade_option = option_items[trade_option][0]
                    break # Exit the loop on valid selection
                else:
                    print(colored(f'Invalid trade option. Please select a number from 1 to {len(option_items)}', 'yellow'))

            # Prompt for profit target
            while True:
                print('\nMinimum: ' + colored('1', 'blue'))
                print('Maximum: ' + colored('1000000', 'yellow'))
                profit_target = input(colored('Enter your profit target: ', 'green'))
                profit_target = int(profit_target) if profit_target.isdigit() else -1
                if 1 <= profit_target <= 1000000:
                    break # Exit the loop on valid selection
                else:
                    print(colored('Invalid profit target. Please select a number from 1 to 1000000', 'yellow'))

            # Prompt for loss target
            while True:
                print('\nMinimum: ' + colored('1', 'blue'))
                print('Maximum: ' + colored('1000000', 'yellow'))
                loss_target = input(colored('Enter your loss target: ', 'red'))
                loss_target = int(loss_target) if loss_target.isdigit() else -1
                if 1 <= loss_target <= 1000000:
                    break # Exit the loop on valid selection
                else:
                    print(colored('Invalid loss target. Please select a number from 1 to 1000000', 'yellow'))

            # Set the user input
            user_input = {
                'account_type': account_type,
                'trading_type': trading_type,
                'bet_level': bet_level,
                'bet_amounts': bet_amounts,
                'financial_instruments': financial_instruments,
                'market_type': market_type,
                'time_option': time_option,
                'trade_time': trade_time,
                'minimum_return': minimum_return,
                'trade_option': 'random',
                #'trade_option': trade_option,
                'profit_target': profit_target,
                'loss_target': loss_target
            }
            file_put_contents (f'{CONFIG_DIR}user_input.json', json.dumps(user_input))
            try:
                # Run the browser script
                await run_browser_script(user_input)
            except TargetClosedError:
                print("Context or page is closed")
            except Exception as e:
                print(f"An error occurred while running the browser script: {e}")
            break # Exit Main loop
        else:
            print(colored('Error connecting to qxbroker.com server.', 'red'))

# Run the main function asynchronously
if __name__ == '__main__':
    try:
        asyncio.run(main())
    finally:
        input('Done !')
        os._exit(0)
