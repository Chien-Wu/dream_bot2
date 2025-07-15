"新加入用戶的歡迎訊息

1. 新用戶加入，傳送「新加入訊息」，並通知管理員。
2. 判斷是否已回傳「單位基本資料」，模糊判斷抓關鍵字就好。

- 已回傳，傳送「歡迎訊息」並通知管理員。
- 未回傳，傳送「提醒訊息」，並拒絕回答問題。完成後，傳送「歡迎訊息」並通知管理員。"

將單位資料存進資料庫

「新加入訊息」（Line@已設定）
{Nickname}您好，歡迎您加入一起夢想｜微型社福專用！

一起夢想成立於 2012 年，致力於讓所有的微型社福無後顧之憂。多年來，我們踏遍台灣，拜訪近 3 千個社福團體，感受著每個角落的溫暖與力量。

感謝您的加入，請提供以下資訊：
1、單位名稱：
2、服務縣市：
3、聯絡人職稱＋姓名＋電話：
4、服務對象（可複選）：弱勢兒少、中年困境、孤獨長者、無助動物

加入臉書社團獲得最新消息：https://godreamer.pse.is/3qu2vc

讓我們攜手成為微型社福的支持者，一起為更美好的明天努力！

--
「單位基本資料」
1、單位名稱：
2、服務縣市：
3、聯絡人職稱＋姓名＋電話：
4、服務對象（可複選）：弱勢兒少、中年困境、孤獨長者、無助動物

--
「歡迎訊息」

- 已收到資料並完成建檔！很高興認識貴單位，一起夢想會持續支持微型社福，期待未來有更多交流 🤜🏻🤛🏻

--
「提醒訊息」
感謝您的加入，請先提供以下資訊：
1、單位名稱：
2、服務縣市：
3、聯絡人職稱＋姓名＋電話：
4、服務對象（可複選）：弱勢兒少、中年困境、孤獨長者、無助動物

1.  Data Detection Keywords

Please specify which keywords should trigger "data provided":

- Should it detect "單位名稱: XXX" format?
- Or just presence of keywords like "單位名稱", "服務縣市"? use chatgpt api (non-assistant) to check what user has filled in, and generate hint for user to finish
- All 4 fields required or partial data accepted? yes, all required

2. Database Requirements

- New table organization_data or extend existing tables? new table
- Should it store raw messages or parsed fields?
- What validation rules for each field? find a good way to implement

3. Blocking Behavior

- Block ALL messages until data provided?yes
- Allow handover requests through?yes
- How to handle AI confidence-based routing?

4. State Management

- Store user state in database or memory? yes
- What happens if user provides data across multiple messages? fill in some data first
- How to reset state if needed?

5. Message Timing

- Should welcome message be immediate or delayed? immediate
- How to coordinate with LINE@ auto-reply?
- What if user sends messages before completing data?
