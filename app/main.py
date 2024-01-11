import uvicorn
import redis  
from config.logger import logger
from config import config
from fastapi import FastAPI, Header, Body, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from utils import LineCourtUtils
from linebot import LineBotApi, WebhookHandler, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, JoinEvent, TextMessage, TextSendMessage, TemplateSendMessage, ButtonsTemplate, MessageTemplateAction, FollowEvent, MessageAction, QuickReplyButton, QuickReply


app = FastAPI()

# 必須放上自己的Channel Access Token 
line_bot_api = LineBotApi(config.line_bot_access_token)  
# 必須放上自己的Channel Secret
parser = WebhookParser(config.line_bot_channel_secret)
handler = WebhookHandler(config.line_bot_channel_secret)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://localhost:3100', 'https://tool.joda.tw'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_request(request: Request, call_next):
    # Get the client's IP address from the request headers
    ip = request.client.host

    # Log the IP address and request information
    log_message = f"Received request from {ip}: {request.method} {request.url}"
    logger.info(log_message)

    # Call the next middleware or the request handler
    response = await call_next(request)

    return response

# 初始化redis物件
r = redis.Redis(host=config.redis_host, port=config.redis_port,
                decode_responses=True)  
                

'''
--------------------------- 處理 LINE BOT 訊息  ---------------------------
'''

# 監聽所有來自 /callback 的 Post Request 
@app.post("/line-bot-callback") 
async def lineBotCallback(request: Request):     
    signature = request.headers["X-Line-Signature"]
    body = await request.body()
    logger.info('signature:')
    logger.info(signature)
    logger.info('body:')
    logger.info(body)
    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Missing Parameters")
    return "OK"



@handler.add(JoinEvent)
def handling_join(event):
    replyToken = event.reply_token

    msg = TemplateSendMessage(
        alt_text = '歡迎使用揪團報名小幫手',
        template=ButtonsTemplate(
            title='歡迎使用揪團報名小幫手',
            text='初次使用請先註冊群組，執行註冊群組的用戶將擁有小幫手的管理員權限',
            actions=[
                MessageTemplateAction(
                    label='註冊群組',
                    text='#註冊群組',
                ),
                MessageTemplateAction(
                    label='查看功能清單',
                    text='#功能',
                ),
                MessageTemplateAction(
                    label='查看管理員功能',
                    text='#管理員功能',
                ),
            ]
        )
    )
    line_bot_api.reply_message(reply_token=replyToken, messages=msg)
        

@handler.add(MessageEvent, message=(TextMessage))
def handling_message(event):


    if isinstance(event.message, TextMessage):
        
        try:
            replyToken = event.reply_token
            logger.info("replytoken")
            logger.info(replyToken)

            # if event.source.type != 'group':
            #     raise ValueError('請將機器人邀請至球隊群組內使用，謝謝')
                
            userId = event.source.user_id
            groupId = event.source.group_id
            text = event.message.text

            if not text.startswith("#"):
                return

            text = text.replace('#', '')
            group_summary = line_bot_api.get_group_summary(groupId)
            groupName = group_summary.group_name

            userProfile = line_bot_api.get_group_member_profile(groupId, userId)
            userName = userProfile.display_name
            
            msg = ''

            # 取得群組所有場次
            courtNos = LineCourtUtils.getAllCourtNos(groupId)

            if '註冊群組' == text:
                msg = LineCourtUtils.addGroup(groupId, groupName, userId, userName)

            elif '' == text:

                '''
                場次資訊:
                    場次A
                    場次B
                    ...

                我要報名
                    報名 A 場次
                    報名 B 場次
                    取消報名 A 場次
                    取消報名 B 場次
                    若要幫非群組內好友報名，手動輸入： #A+2 好友A 好友B， #B+3 好友A 好友B


                其他資訊:
                    管理員清單
                    季打清單

                管理員功能
                    開場
                    刪除場次
                    清空場次報名清單(自動加入季打名單)
                    新增管理員
                    移除管理員
                    新增季打
                    移除季打
                '''
                

                msg = LineCourtUtils.func_card(groupId)

                # template_message = TemplateSendMessage(
                #     alt_text='CarouselTemplate',
                #     template=msg
                # )
                
                line_bot_api.reply_message(reply_token=replyToken, messages=msg)

         
  
            elif '管理員功能' == text:
                
                if LineCourtUtils.needAdminOrError(groupId, userId):
                    msg = LineCourtUtils.admin_func_card(groupId)
                    line_bot_api.reply_message(reply_token=replyToken, messages=msg)

            elif text.startswith("新增管理員"):
                if LineCourtUtils.needAdminOrError(groupId, userId):
                    mentionees = LineCourtUtils.getMentioneesOrError(event)
                    addIds = []
                    addNames = []
                    for mentionee in mentionees:
                        addIds.append(mentionee.user_id)
                        addNames.append(line_bot_api.get_group_member_profile(groupId, mentionee.user_id).display_name)

                    msg = LineCourtUtils.addAdmins(groupId, addIds, addNames)

            elif text.startswith("移除管理員"):
                if LineCourtUtils.needAdminOrError(groupId, userId):
                    mentionees = LineCourtUtils.getMentioneesOrError(event)
                    delIds = []
                    for mentionee in mentionees:
                        delIds.append(mentionee.user_id)
                    msg = LineCourtUtils.removeAdmins(line_bot_api, groupId, delIds)

            elif text.startswith("開場"):
                if LineCourtUtils.needAdminOrError(groupId, userId):
                    arr = text.split(' ')
                    date = arr[1] 
                    time = arr[2] 
                    place = arr[3] 
                    total = arr[4]
                    courtCost = arr[5]
                    price = arr[6]
                    msg = LineCourtUtils.addCourt(groupId, date, time, place, total, courtCost, price)

            elif text.startswith("刪場"):
                if LineCourtUtils.needAdminOrError(groupId, userId):
                    courtNo = text.replace("刪場", "").replace("-", "").replace(":", "").replace(" ", "").strip()
                    if courtNo:
                        msg = LineCourtUtils.delCourt(groupId, courtNo)

            elif text.startswith("清空"):
                if LineCourtUtils.needAdminOrError(groupId, userId):
                    courtNo = text.replace("清空", "").replace("-", "").replace(":", "").replace(" ", "").strip()
                    if courtNo:
                        msg = LineCourtUtils.emptyList(groupId, courtNo)

            elif text.startswith("完成"):
                if LineCourtUtils.needAdminOrError(groupId, userId):
                    courtNo = text.replace("完成", "").replace("-", "").replace(":", "").replace(" ", "").strip()
                    if courtNo:
                        msg = LineCourtUtils.finishCourt(groupId, courtNo)

            elif text.startswith("預設名單"):
                if LineCourtUtils.needAdminOrError(groupId, userId):
                    text = text.replace("預設名單", "").strip()
                    if text == '':
                        # 查詢預設名單
                        names = r.hget(f"line-court:{groupId}:info", 'defaultNames')
                        if names:
                            msg = f"預設名單：{names}"
                        else:
                            msg = "尚未新增預設名單"
                    else:
                        arr = text.split(' ')
                        names = []
                        for name in arr:
                            names.append(name)
                        r.hset(f"line-court:{groupId}:info", 'defaultNames', ','.join(names))
                        msg = f"預設名單：{','.join(names)}"


            elif text.startswith("新增預設名單"):
                if LineCourtUtils.needAdminOrError(groupId, userId):
                    text = text.replace("新增預設名單", "").strip()
                    arr = text.split(' ')
                    names = r.hget(f"line-court:{groupId}:info", 'defaultNames')
                    if names:
                        names = names.split(',')
                    else:
                        names = []

                    for name in arr:
                        if name not in names:
                            names.append(name)
                    r.hset(f"line-court:{groupId}:info", 'defaultNames', ','.join(names))
                    msg = f"預設名單：{','.join(names)}"
            elif text.startswith("刪除預設名單"):
                if LineCourtUtils.needAdminOrError(groupId, userId):
                    text = text.replace("刪除預設名單", "").strip()
                    arr = text.split(' ')
                    names = r.hget(f"line-court:{groupId}:info", 'defaultNames')
                    if names:
                        names = names.split(',')
                    else:
                        names = []
                        
                    for name in arr:
                        if name in names:
                            names.remove(name)
                            
                    r.hset(f"line-court:{groupId}:info", 'defaultNames', ','.join(names))
                    msg = f"預設名單：{','.join(names)}"

            elif text.startswith("新增季打"):
                if LineCourtUtils.needAdminOrError(groupId, userId):
                    text = text.replace("新增季打", "").strip()
                    arr = text.split(' ')
                    for courtNo in arr:
                        if courtNo in courtNos:
                            mentionees = LineCourtUtils.getMentioneesOrError(event)
                            addIds = []
                            for mentionee in mentionees:
                                addIds.append(mentionee.user_id)
                            msg = LineCourtUtils.addSeasonList(line_bot_api, groupId, courtNo, addIds)

            elif text.startswith("移除季打"):
                if LineCourtUtils.needAdminOrError(groupId, userId):
                    text = text.replace("移除季打", "").strip()
                    arr = text.split(' ')
                    for courtNo in arr:
                        if courtNo in courtNos:
                            mentionees = LineCourtUtils.getMentioneesOrError(event)
                            delIds = []
                            for mentionee in mentionees:
                                delIds.append(mentionee.user_id)            
                            msg = LineCourtUtils.removeSeasonList(line_bot_api, groupId, courtNo, delIds)

            elif '管理員清單' == text:
                msg = LineCourtUtils.listAdminNames(groupId)

            elif text.startswith("場次資訊"):
                courtNo = text.replace("場次資訊", "").replace("-", "").replace(":", "").replace(" ", "").strip()
                if courtNo:
                    msg = LineCourtUtils.courtInfo(line_bot_api, groupId, courtNo)

            elif all(char in courtNos for char in text):
                '''
                    自己報名用
                '''
                for courtNo in text:
                    msg += LineCourtUtils.signUp(line_bot_api, groupId, courtNo, userId, userName)

            elif text.startswith("代報"):
                '''
                    幫人報名
                '''
                text = text.replace("代報", "").strip()

                arr = text.split(' ')

                # 取得場次編號
                courtNo = arr.pop(0)

                msg = LineCourtUtils.signUpMultiple(groupId, courtNo, arr, userId)

            elif text.startswith("名單"):
                courtNo = text.replace("名單", "").replace("-", "").replace(":", "").replace(" ", "").strip()
                if courtNo:
                    msg += LineCourtUtils.list(groupId, courtNo)
                    msg += '\n'
                    msg += LineCourtUtils.waitList(groupId, courtNo)

            elif text.startswith("季打名單"):
                courtNo = text.replace("季打名單", "").replace("-", "").replace(":", "").replace(" ", "").strip()
                if courtNo:
                    msg = LineCourtUtils.Seasonlist(groupId, courtNo)

            elif text.startswith("取消"):
                text = text.replace("取消", "").strip()
                arr = text.split(' ')
                courtNo = arr.pop(0)

                if len(arr) == 0:
                    # 沒有輸入名字，取消自己
                    arr.append(userName)
                    msg = LineCourtUtils.signOut(line_bot_api, groupId, courtNo, arr, userId)
                else:
                    # 取消輸入的名單
                    msg = LineCourtUtils.signOut(line_bot_api, groupId, courtNo, arr, userId)

            if msg:
                line_bot_api.reply_message(reply_token=replyToken, messages=TextSendMessage(text=msg))

        except ValueError as ve:
            line_bot_api.reply_message(reply_token=replyToken, messages=TextSendMessage(text=str(ve)))
            logger.error(ve)
        except Exception as e:
            logger.error(e)
            raise e

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
