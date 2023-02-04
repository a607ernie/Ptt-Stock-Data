# Ptt-Stock-Data

# Goal

只抓取標題分類為`標的`或是`Re:標的`的文章，內容格式都一樣。

- `標的`
```json
"[標的] 8261 富鼎  跟著董事一起賣": {
        "STOCK_ID": "8261",
        "TITLE": "[標的] 8261 富鼎  跟著董事一起賣",
        "ID": "M.1673535142.A.C90",
        "LINK": "https://www.ptt.cc/bbs/Stock/M.1673535142.A.C90.html",
        "AUTHOR": "n88713117",
        "CONTENT": "long text",
        "TIME": "Thu Jan 12 22:52:20 2023",
        "MESSAGE_ALL": 38,
        "BOO": 0,
        "PUSH": 21,
        "MESSAGE_COUNT": 21,
        "NEUTRAL": 17,
        "TAG": "標的"
}
```

- `Re:標的`
```json
"Re: [標的] TSLA, AMD, TSM.US 歐印誰 討論": {
    "STOCK_ID": 0,
    "TITLE": "Re: [標的] TSLA, AMD, TSM.US 歐印誰 討論",
    "ID": "M.1673549109.A.6D3",
    "LINK": "https://www.ptt.cc/bbs/Stock/M.1673549109.A.6D3.html",
    "AUTHOR": "andylu1207",
    "CONTENT": "long text",
    "TIME": "Fri Jan 13 02:45:07 2023",
    "MESSAGE_ALL": 55,
    "BOO": 4,
    "PUSH": 19,
    "MESSAGE_COUNT": 15,
    "NEUTRAL": 32,
    "TAG": "Re標的"
}
```

# 功能

- 多執行緒爬取Ptt文章
- 可透過`slack`發送通知


# run on local


如果要使用`Slack`，在local端新增一個`.env` file，內容為

```text
SLACK_WEBHOOK = "slack-webhook <-自行替換"
```
並將以下程式碼的註釋打開

```python
# test .ENV
# use in local 
config = dotenv_values(".env")
SLACK_WEBHOOK = config['SLACK_WEBHOOK']
```

- 如果不使用`Slack`，則自行mark掉相關code

# run on github or server

在github repo setting中，設置`SLACK_WEBHOOK`，即可透過`Slack`接收通知

```python
# prod .ENV
# use in github or production
SLACK_WEBHOOK = os.getenv('SLACK_WEBHOOK')
```
