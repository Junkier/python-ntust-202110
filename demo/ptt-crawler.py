#!/usr/bin/env python
# coding: utf-8

# In[17]:


## 引用套件
import requests , arrow , time
import os
import pandas as pd 

from bs4 import BeautifulSoup as bs 

## 定義 function

# 移除標籤
# - div.article-metaline
# - div.article-metaline-right
# - span.f2
def remove_dirty_tag(soup):
    
    # 若存在 , 則移除標籤
    if len(soup.select("div.article-metaline")) >0 :
        
        # 標籤可能多項 , 使用 for-loop 移除
        for tag in soup.select("div.article-metaline"):
            tag.extract()
            
    if len(soup.select("div.article-metaline-right")) >0 :
        for tag in soup.select("div.article-metaline-right"):
            tag.extract()
            
    if len(soup.select("span.f2")) >0 :
        for tag in soup.select("span.f2"):
            tag.extract()
    
    return soup 

# 回應資料
def get_resp_data(ele):
    span_tags = ele.select("span")
    return {
        "tag"     : span_tags[0].text.strip(),
        "author"  : span_tags[1].text.strip(),
        "content" : span_tags[2].text.replace(": ","").strip(), 
        "time"    : span_tags[3].text.strip()
    }


def get_data(soup,link):
    ### 抓取本文的 作者 , 看板 , 標題 , 時間 
    span_tags = soup.select("div#main-content span.article-meta-value")

    # 作者
    author = span_tags[0].text

    # 看板
    category = span_tags[1].text

    # 標題
    title = span_tags[2].text

    # 時間
    time = arrow.get( span_tags[3].text , "ddd MMM DD HH:mm:ss YYYY").format("YYYY-MM-DD HH:mm:ss")

    ### 抓取本文的 內容 , 回應
    push_tags = soup.select("div#main-content div.push")
    resp_data = []

    if len(push_tags) >0:

        for ele in push_tags:
            ele.extract()  # 宣告從 div#main-content 中,拔除 div.push 標籤

            resp = get_resp_data(ele)

            resp_data.append(resp)

    ### 內容
    soup = remove_dirty_tag(soup)
    content = soup.select("div#main-content")[0].text.strip()
    
    return {
        "author" : author,
        "category" : category,
        "title" : title,
        "time" : time,
        "resp_data" : resp_data,
        "content" : content,
        "link"     : link   # 新增連結欄位
    }



### main 程式

## 取得本文 source code
url = "https://www.ptt.cc/bbs/Stock/index.html"
headers = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"
}

res = requests.get(url,headers=headers)
soup = bs(res.text,"lxml")

links = []

print("* 取得本文 source code 完成！")


##  抓取首頁文章連結
for a_tag in soup.select("div#main-container div.r-ent div.title a"):
    
    # 過濾 版規 & 盤後閒聊 / 盤中閒聊
    title = a_tag.text
    
    if "股票板板規" in title or "盤後閒聊" in title or "盤中閒聊" in title :
        continue # 跳過此步, 執行下一動迴圈
    else:
        url = "https://www.ptt.cc" + a_tag["href"]
        links.append(url)
        
print("* 抓取首頁文章連結 完成！")

        
##  抓取 分頁文章 連結
for i in range(1,6):
    
    # 建構 '上頁' 連結
    link = soup.select("div#action-bar-container div.btn-group-paging a")[1]["href"]
    previous_link = "https://www.ptt.cc" + link
    
    time.sleep(0.2)

    res = requests.get(previous_link,headers=headers)
    soup = bs(res.text,"lxml")

    for a_tag in soup.select("div#main-container div.r-ent div.title a"):

        # 過濾 版規 & 盤後閒聊 / 盤中閒聊
        title = a_tag.text

        if "股票板板規" in title or "盤後閒聊" in title or "盤中閒聊" in title :
            continue # 跳過此步, 執行下一動迴圈
        else:
            url = "https://www.ptt.cc" + a_tag["href"]
            links.append(url)
            
    print("{} is ok.".format(previous_link))

print("* 抓取分頁文章連結 完成！")


dataList = []
for url in links[:10]:      ### 教學用 , 先限定10筆
    res2 = requests.get(url,headers=headers)
    soup2 = bs(res2.text,"lxml")

    # 透過 get_data 從 soup2 解析出 dict 資料
    data = get_data(soup2,url)
    dataList.append(data)

    print("{} is ok.".format(url))
    
print("* 抓取文章資料 完成！")

### 資料落地

## 檢查 sample 資料夾是否存在
#   不存在 -> 新建一個資料夾
if not os.path.exists("sample"):
    os.mkdir("sample")
    
## 本文資料放入 DataFrame
df = pd.DataFrame(dataList)
df = df[["title","category","time","author","content","link"]]
df.columns = ["標題","分類","時間","作者","內容","連結"]

## 回應資料放入另一個 DataFrame
i=0
resp_data = []

for ele in dataList:
    for resp_ele in ele["resp_data"]:
        resp_ele["article_no"] = i
        resp_data.append(resp_ele)
    i+=1
    
resp_df = pd.DataFrame(resp_data)
resp_df = resp_df[["article_no","tag","author","content","time"]]
resp_df.columns = ["文章編號","推文類型","作者","內容","時間"]
resp_df


## 輸出成 excel
file_name = arrow.get().shift(hours=8).format("YYYY-MM-DD_HH_mm_ss")

with pd.ExcelWriter('sample/{}.xlsx'.format(file_name)) as writer:  
    df.to_excel(writer, sheet_name='文章本文')
    resp_df.to_excel(writer, sheet_name='回應內容',index=False)
        
print("* 資料落地 完成！")

print("Done.")

