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
import datetime

semaphore = threading.Semaphore(30)

class Stock(object):
    def __init__(self):
        self.base_url = "https://www.ptt.cc/"
        self.fetch_flag = False
        self.url = 'https://www.ptt.cc/bbs/Stock/index.html'
        #1. get the index page & get the next page url
        self.data, self.upURL = self.fetchpage(self.url)  # step-1
        
    #上一頁
    def uppage(self,sp):
        uppage = self.base_url+sp.find("div",{'class':'btn-group btn-group-paging'}).find_all('a')[1]['href']
        return uppage

    #request to the page and return a beautifulsoup object
    def fetchpage(self,current_page):
        data = []
        if self.fetch_flag == True: # current_page first is a url , then always number like 5009....
            url = 'https://www.ptt.cc//bbs/Stock/index%s.html' % current_page
            print(url)
            r = requests.get(url)
        else:
            print(current_page)
            r = requests.get(current_page)
        sp = BeautifulSoup(r.text, 'lxml')
        upURL = self.uppage(sp)
        rent = sp.find_all('div', {'class': 'r-ent'})
        for page in rent:
            try:
                title = page.find('div', {'class': 'title'}).a.text
                # check the title include [標的]
                if "[標的]" in title:
                    try:
                        stock_id = re.findall(r"[0-9]{4}", title)[0]
                    except:
                        stock_id = 0
                    pagelink = "https://www.ptt.cc" + page.find('div', {'class': 'title'}).a['href']
                    article_id = page.find('div', {'class': 'title'}).a['href'].split('/')[-1].split('.html')[0]
                    author = page.find('div', {'class': 'author'}).text
                    if 'Re' not in title:
                        content_tag = "標的"
                    else:
                        content_tag = "Re標的"
                    temp = {
                        'title':title,
                        'article_id' : article_id,
                        'pagelink': pagelink,
                        'author': author,
                        'content_tag':content_tag,
                        'stock_id':stock_id
                    }
                    data.append(temp)
            except:
                pass
        return data,upURL

    #parse article , and build a payload
    def parsepage(self,item):
        payload = []
        r = requests.get(item['pagelink'])
        sp = BeautifulSoup(r.text, 'lxml')

        content = sp.find('div', {'id': 'main-content'}).text
        try:
            date = sp.find('span', {'class': 'article-meta-tag'}, text=re.compile('時間')).next.next.text
        except:
            pass


        message = sp.find_all('div', {'class': 'push'})
        message_all = len(sp.find_all('div', {'class': 'push'}))
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

    # multi thread 
    def parsethread(self,upURL,q):
        # 取得旗標
        semaphore.acquire()
        data, upURL = self.fetchpage(upURL)
        for item in data:
            payload = self.parsepage(item)
            q.put_nowait(payload)
        semaphore.release()


    # class main
    def __main__(self,page_num):
        result=[]
        for item in self.data:
            _item = self.parsepage(item)
            result.append(_item)

        current_page = int(self.upURL.split('index')[1].split('.html')[0])
        self.fetch_flag=True

        #5. mutil thread to run the for loop
        threads = []
        q = Queue()
        for idx,page in enumerate(range(current_page,int(current_page-page_num),-1)):
            threads.append(threading.Thread(target=self.parsethread, args=(page,q,)))
            threads[idx].start()
            time.sleep(0.5)
        for i in range(len(threads)):
            threads[i].join()
        for i in range(q.qsize()):
            result.append(q.get_nowait())

        # process the result 
        # change list to json format
        res = {}
        for i in range(len(result)):
            res[result[i][0]['TITLE']] = result[i][0]
        
        return res



#############
# slack
#############
dict_headers = {'Content-type': 'application/json'}
config = dotenv_values(".env")

loc_dt = datetime.datetime.today() 
loc_dt_format = loc_dt.strftime("%Y/%m/%d %H:%M:%S")
slack_content = {
	"blocks": [
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "*PTT STOCK* :zap: {}".format(loc_dt_format)
			}
		},
		{
			"type": "divider"
		}
	]
}


def slack_notify(data):
    df = pd.DataFrame(data).T.reset_index()
    filter_df = df[['STOCK_ID','TITLE','AUTHOR','LINK']]

    for index, row in filter_df.iterrows():
        slack_content['blocks'].append({'type': 'section', 'text': {'type': 'mrkdwn',"text":"\n*<{}|{}>*\n*STOCK ID* : {} \n*AUTHOR* : {}\n"\
        .format(row['LINK'],row['TITLE'],row['STOCK_ID'],row['AUTHOR'])}})
    
        slack_content['blocks'].append({'type': 'divider'})
    
    rtn = requests.post(config['SLACK_WEBHOOK'], data=json.dumps(slack_content),headers=dict_headers)
    print(rtn)

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
    df = pd.read_json(json_object).T
    df.to_csv('ptt_stock.csv',encoding='utf-8-sig', index=False)

    slack_notify(result)