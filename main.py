import sys
sys.path.append('.')
import time
import requests
from bs4 import BeautifulSoup
import re,json,lxml
import threading
from queue import Queue
import pandas as pd
from dotenv import dotenv_values
import os
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError


semaphore = threading.Semaphore(10)

class Stock(object):
    def __init__(self):
        self.base_url = "https://www.ptt.cc/"
        self.fetch_flag = False
        self.url = 'https://www.ptt.cc/bbs/Stock/index.html'
        # Step 1: Get the index page and the next page URL
        self.data, self.upURL = self.fetchpage(self.url)

    # Request the page and return a BeautifulSoup object
    def fetchpage(self, current_page):
        data = []
        if self.fetch_flag:  # current_page first is a URL, then always a number like 5009...
            url = f'https://www.ptt.cc/bbs/Stock/index{current_page}.html'
            print(url)
            r = requests.get(url)
        else:
            print(current_page)
            r = requests.get(current_page)
        
        sp = BeautifulSoup(r.text, 'lxml')
        
        # Extract the "上一頁" URL directly here
        paging_div = sp.find("div", {'class': 'btn-group btn-group-paging'})
        if paging_div:
            upURL = paging_div.find_all('a')[1]['href']
        else:
            upURL = None
        
        rent = sp.find_all('div', {'class': 'r-ent'})
        for page in rent:
            try:
                title = page.find('div', {'class': 'title'}).a.text
                # Check if the title includes [標的]
                if "[標的]" in title:
                    try:
                        stock_id = re.findall(r"[0-9]{4}", title)[0]
                    except:
                        stock_id = 0
                    pagelink = "https://www.ptt.cc" + page.find('div', {'class': 'title'}).a['href']
                    article_id = page.find('div', {'class': 'title'}).a['href'].split('/')[-1].split('.html')[0]
                    author = page.find('div', {'class': 'author'}).text
                    content_tag = "標的" if 'Re' not in title else "Re標的"
                    temp = {
                        'title': title,
                        'article_id': article_id,
                        'pagelink': pagelink,
                        'author': author,
                        'content_tag': content_tag,
                        'stock_id': stock_id
                    }
                    data.append(temp)
            except:
                pass
        
        return data, upURL

    # Parse an article and build a payload
    def parsepage(self, item):
        payload = []
        r = requests.get(item['pagelink'])
        sp = BeautifulSoup(r.text, 'lxml')

        content = sp.find('div', {'id': 'main-content'}).text
        try:
            date = sp.find('span', {'class': 'article-meta-tag'}, text=re.compile('時間')).next.next.text
        except:
            date = None

        message = sp.find_all('div', {'class': 'push'})
        message_all = len(message)
        push = 0
        boo = 0
        neutral = 0
        for i in message:
            try:
                tag = i.find('span', {'class': 'hl push-tag'}).text.strip()
            except:
                tag = i.find('span', {'class': 'f1 hl push-tag'}).text.strip()
            if tag == '推':
                push += 1
            elif tag == '噓':
                boo += 1
            elif tag == '→':
                neutral += 1
        message_count = push - boo
        data = {
                'STOCK_ID': item['stock_id'],
                "TITLE": item['title'],
                "ID": item['article_id'],
                "LINK":item['pagelink'],
                "AUTHOR": item['author'],
                "CONTENT": content,
                "TIME": date,
                "MESSAGE_ALL": message_all,
                "BOO": boo,
                "PUSH": push,
                "MESSAGE_COUNT": message_count,
                "NEUTRAL": neutral,
                "TAG":item['content_tag']
        }
        payload.append(data)
        return payload

    # Multi-thread processing
    def parsethread(self, upURL, q):
        # Acquire semaphore
        semaphore.acquire()
        data, upURL = self.fetchpage(upURL)
        for item in data:
            payload = self.parsepage(item)
            q.put_nowait(payload)
        semaphore.release()

    # Class main method
    def __main__(self, page_num):
        result = []
        for item in self.data:
            _item = self.parsepage(item)
            result.append(_item)

        current_page = int(self.upURL.split('index')[1].split('.html')[0])
        self.fetch_flag = True

        # Multi-thread loop
        threads = []
        q = Queue()
        for idx, page in enumerate(range(current_page, int(current_page - page_num), -1)):
            threads.append(threading.Thread(target=self.parsethread, args=(page, q,)))
            threads[idx].start()
            time.sleep(0.5)
        for i in range(len(threads)):
            threads[i].join()
        for i in range(q.qsize()):
            result.append(q.get_nowait())

        # Process the result
        # Change list to JSON format
        res = {}
        for i in range(len(result)):
            res[result[i][0]['TITLE']] = result[i][0]

        return res




#############
# slack
#############
dict_headers = {'Content-type': 'application/json'}

# test .ENV
# use in local 
#config = dotenv_values(".env")
#SLACK_WEBHOOK = config['SLACK_WEBHOOK']

# prod .ENV
# use in github or production
# SLACK_WEBHOOK = os.getenv('SLACK_WEBHOOK')

# slack_content = {
# 	"blocks": [
# 		{
# 			"type": "section",
# 			"text": {
# 				"type": "mrkdwn",
# 				"text": "*PTT STOCK* :zap:"
# 			}
# 		},
# 		{
# 			"type": "divider"
# 		}
# 	]
# }


def slack_notify(data):
    df = pd.DataFrame(data).T.reset_index()
    filter_df = df[['STOCK_ID','TITLE','AUTHOR','LINK']]

    for index, row in filter_df.iterrows():
        slack_content['blocks'].append({'type': 'section', 'text': {'type': 'mrkdwn',"text":"\n*<{}|{}>*\n*STOCK ID* : {} \n*AUTHOR* : {}\n"\
        .format(row['LINK'],row['TITLE'],row['STOCK_ID'],row['AUTHOR'])}})
    
        slack_content['blocks'].append({'type': 'divider'})
    
    rtn = requests.post(SLACK_WEBHOOK, data=json.dumps(slack_content),headers=dict_headers)
    print(rtn)

#############
# LINE
#############
# test .ENV
# use in local 

#config = dotenv_values(".env")
#LINE_Channel_ACCESS_TOKEN = config['LINE_Channel_ACCESS_TOKEN']
#LINE_CHANNEL_ID = config['LINE_CHANNEL_ID']

# prod .ENV
# use in github or production
# LINE_Channel_ACCESS_TOKEN = os.getenv('LINE_Channel_ACCESS_TOKEN')
# LINE_CHANNEL_ID = os.getenv('LINE_CHANNEL_ID')

def line_notify(data):
    line_bot_api = LineBotApi(LINE_Channel_ACCESS_TOKEN)
    line_content = ''
    df = pd.DataFrame(data).T.reset_index()
    filter_df = df[['STOCK_ID','TITLE','AUTHOR','LINK']]

    # build context
    for index, row in filter_df.iterrows():
        try:
            line_content += ('文章標題:{title}  \n--作者:{author}\n'
                                '--股票名稱:{stock_id}\n\n{link}\n\n') \
                        .format(title=row['TITLE'], author=row['AUTHOR'],stock_id=row['STOCK_ID'],link=row['LINK'])
        except:
            line_content = 'something wrong!'
            #print("something wrong!")
    
    # push message
    try:
        line_bot_api.push_message(LINE_CHANNEL_ID, TextSendMessage(text=line_content))
    except LineBotApiError as e:
        line_bot_api.push_message(LINE_CHANNEL_ID, TextSendMessage(text=line_content))
        print(e)


####################
# run code
####################

if __name__ == '__main__':
    stock = Stock()

    # ptt page number
    page_num=5
    result = stock.__main__(page_num)

    # .JSON
    json_object = json.dumps(result, indent=4,ensure_ascii=False)
    with open("ptt_stock.json", "w",encoding='utf-8') as outfile:
        outfile.write(json_object)
    
    # .CSV
    # df = pd.read_json(json_object).T
    # df.to_csv('ptt_stock.csv',encoding='utf-8-sig', index=False)

    #slack_notify(result)
    # line_notify(result)