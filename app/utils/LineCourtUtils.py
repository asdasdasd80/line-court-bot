import json
import codecs
from redis import Redis
from linebot.models import (
    FlexSendMessage, BubbleContainer, BoxComponent, TextComponent, ButtonComponent, SeparatorComponent,
    CarouselTemplate, CarouselColumn, MessageAction ,TextComponent, ButtonComponent, FlexSendMessage,
    CarouselContainer
)

class User():
    def __init__(self, userId, userName):
        self.userId = userId
        self.userName = userName

def addGroup(r:Redis, groupId, groupName, adminUserId, adminUserName):
    '''
        初始化建立群組
    '''
    key = f'line-court:{groupId}:info'
    
    if r.exists(key) == 1:
        adminNames = json.loads(r.hget(key, 'adminNames'))
        raise ValueError(f'已註冊過群組資訊，管理員為{", " .join(adminNames)}')
    
    adminIds = [adminUserId]
    adminNames = [adminUserName]
    r.hset(key, 'adminIds', json.dumps(adminIds))
    r.hset(key, 'adminNames', json.dumps(adminNames))
    r.hset(key, 'groupName', groupName)
    message = f'新增群組 {groupName} 成功，管理員為 {adminUserName}，請使用"指令"確認功能清單 '
    return message

def addAdmins(r:Redis, groupId, addIds, addNames):
    '''
        新增管理員
    '''
    key = f'line-court:{groupId}:info'
    
    if r.exists(key) == 0:
        raise ValueError(f'請先註冊群組')
    
    if len(addIds) <= 0:
        raise ValueError(f'請使用tag方式標示出要賦予管理員權限的成員')
    
    adminIds = json.loads(r.hget(key, 'adminIds'))
    adminNames = json.loads(r.hget(key, 'adminNames'))

    adminIds = adminIds + addIds
    adminNames = adminNames + addNames
    r.hset(key, 'adminIds', json.dumps(adminIds))
    r.hset(key, 'adminNames', json.dumps(adminNames))

    return '新增管理員成功'


def removeAdmins(r:Redis, line_bot_api, groupId, delIds):
    '''
        移除管理員權限
    '''
    key = f'line-court:{groupId}:info'
    if r.exists(key) == 0:
        raise ValueError(f'請先註冊群組')
    
    if len(delIds) <= 0:
        raise ValueError(f'請使用tag方式標示出要移除管理員權限的成員')
    
    delNames = []
    
    adminIds = json.loads(r.hget(key, 'adminIds'))
    adminNames = json.loads(r.hget(key, 'adminNames'))

    for delId in delIds:
        if delId in adminIds:
            delNames.append(getName(line_bot_api, groupId, delId))
            i = adminIds.index(delId)
            del adminIds[i]
            del adminNames[i]

    r.hset(key, 'adminIds', json.dumps(adminIds))
    r.hset(key, 'adminNames', json.dumps(adminNames))
    return f'已移除 {", ".join(delNames)}管理員權限'



def listAdminNames(r:Redis, groupId):
    '''
        列出管理員姓名清單
    '''
    key = f'line-court:{groupId}:info'
    if r.exists(key) == 0:
        raise ValueError(f'請先註冊群組')
    
    adminNames = json.loads(r.hget(key, 'adminNames'))
    return f'管理員清單： {", " .join(adminNames)}'

def listAdminIds(r:Redis, groupId):
    '''
        列出管理員清單
    '''
    key = f'line-court:{groupId}:info'
    if r.exists(key) == 0:
        raise ValueError(f'請先註冊群組')
    
    adminIds = json.loads(r.hget(key, 'adminIds'))
    return adminIds


def addCourt(r:Redis, groupId, courtNo, date, time, place, total):
    '''
        新增場次
    '''
    key = f'line-court:{groupId}:info'
    if r.exists(key) == 0:
        raise ValueError(f'請先註冊群組')

    key = f'line-court:{groupId}:{courtNo}'
    r.hset(key, 'courtNo', courtNo)
    r.hset(key, 'date', date)
    r.hset(key, 'time', time)
    r.hset(key, 'place', place)
    r.hset(key, 'total', total)
    r.hset(key, 'list', '[]')
    r.hset(key, 'waitList', '[]')
    r.hset(key, 'seasonList', '[]')
    return f'開場成功\n場次代號:{courtNo}\n日期:{date}\n時間:{time}\n地點:{place}\n名額:{total}'

def delCourt(r:Redis, groupId, courtNo):
    '''
        刪除場次
    '''
    key = f'line-court:{groupId}:{courtNo}'
    if r.exists(key) == 0:
        raise ValueError(f'查無場次編號:{courtNo}，請重新確認')

    r.delete(key)
    return f'刪除場次 {courtNo} 成功'

def courtInfo(r:Redis, line_bot_api, groupId, courtNo):
    '''
        列出所有場次資訊
    '''
    key = f'line-court:{groupId}:{courtNo}'
    if r.exists(key) == 0:
        raise ValueError(f'查無場次編號:{courtNo}，請重新確認')
    
    courtNo = r.hget(key, 'courtNo')
    date = r.hget(key, 'date')
    time = r.hget(key, 'time')
    place = r.hget(key, 'place')
    total = int(r.hget(key, 'total'))
    signList = json.loads(r.hget(key, 'list'))

    # 場地資訊
    msg = (f'場次代號:{courtNo}\n日期:{date}\n時間:{time}\n地點:{place}\n剩餘名額:{total - len(signList)}\n\n')

    # 報名清單
    msg += list(r, line_bot_api, groupId, courtNo)

    msg += '\n'
    msg += '\n'
    # 候補清單
    msg += waitList(r, line_bot_api, groupId, courtNo)

    return msg

def getAllCourtNos(r:Redis, groupId):
    '''
        取得所有場次代號
    '''
    keys = r.keys(f'line-court:{groupId}:*')
    courtNos = []
    for key in keys:
        if 'info' not in key:
            courtNo = r.hget(key, 'courtNo')
            courtNos.append(courtNo)
    courtNos.sort()
    return courtNos

def needAdminOrError(r:Redis, groupId, userId):
    '''
        是否為管理員
    '''
    key = f'line-court:{groupId}:info'
    if r.exists(key) == 0:
        raise ValueError(f'請先註冊群組')
    
    adminIds = json.loads(r.hget(key, 'adminIds'))
    if userId in adminIds:
        return True
    else:
        raise ValueError(f'您沒有管理員權限，請洽群組管理員')


def signUp(r:Redis, groupId, courtNo, userId, userName):
    '''
        群組成員自行報名
    '''
    key = f'line-court:{groupId}:{courtNo}'
    if r.exists(key) == 0:
        raise ValueError(f'查無場次編號:{courtNo}，請重新確認')
    
    msg = ''
    total = int(r.hget(f'line-court:{groupId}:{courtNo}', 'total'))
    list = json.loads(r.hget(f'line-court:{groupId}:{courtNo}', 'list'))
    current = len(list)
    existUser = [user for user in list if user['userId'] == userId and user['userName'] == userName]
    
    if len(existUser) > 0:
        raise ValueError(f'您已在場次 {courtNo} 名單上，若要幫朋友報名請使用 "代報" 功能')


    if total - current > 0:
        user = User(userId, userName)
        list.append(user)
        r.hset(f'line-court:{groupId}:{courtNo}', 'list', json.dumps(list, default=lambda o: o.__dict__))

        if total - len(list) == 0:
            msg = f'{userName} 報名成功，場次 {courtNo} 已額滿\n'
        else:
            msg = f'{userName} 報名成功，場次 {courtNo} 剩 {total - len(list)} 個名額\n'
    else:
        waitList = json.loads(r.hget(f'line-court:{groupId}:{courtNo}', 'waitList'))
        waitList.append(user)
        r.hset(f'line-court:{groupId}:{courtNo}', 'waitList', json.dumps(waitList, default=lambda o: o.__dict__))
        msg = f'場次 {courtNo} 已額滿，將您排在候補第{len(waitList)}位\n'

    return msg


def signUpMultiple(r:Redis, line_bot_api, groupId, courtNo, userNames, ownerId):
    '''
        一次報名多人
    '''
    key = f'line-court:{groupId}:{courtNo}'
    if r.exists(key) == 0:
        raise ValueError(f'查無場次編號:{courtNo}，請重新確認')
    
    msg = ''

    total = int(r.hget(f'line-court:{groupId}:{courtNo}', 'total'))
    list = json.loads(r.hget(f'line-court:{groupId}:{courtNo}', 'list'))
    waitList = json.loads(r.hget(f'line-court:{groupId}:{courtNo}', 'waitList'))

    for userName in userNames:
        if userName.startswith('@'):
            userName = userName.replace("@", "")

        user = User(ownerId, userName)
        if total - len(list) > 0:
            list.append(json.loads(json.dumps(user, default=lambda o: o.__dict__)))
            msg += f'{userName} 報名成功\n'
        else:
            waitList.append(json.loads(json.dumps(user, default=lambda o: o.__dict__)))
            msg += f'場次 {courtNo} 額滿，{userName} 排在候補第{len(waitList)}位\n'

    r.hset(f'line-court:{groupId}:{courtNo}', 'list', json.dumps(list, default=lambda o: o.__dict__))

    if len(waitList) > 0:
        r.hset(f'line-court:{groupId}:{courtNo}', 'waitList', json.dumps(waitList, default=lambda o: o.__dict__))

    return msg

def signOut(r:Redis, line_bot_api, groupId, courtNo, delNames, ownerId):
    '''
        取消報名
    '''
    key = f'line-court:{groupId}:{courtNo}'
    if r.exists(key) == 0:
        raise ValueError(f'查無場次編號:{courtNo}，請重新確認')
    
    message = ''
    ownerName = getName(line_bot_api, groupId, ownerId)
    adminIds = listAdminIds(r, groupId)
    total = int(r.hget(key, 'total'))
    list = json.loads(r.hget(key, 'list'))

    delUsers = []

    for user in list:
        userName = user['userName']
        userId = user['userId']
        if userName in delNames:
            if userId != ownerId and ownerId not in adminIds:
                raise ValueError(f'{userName} 不是由 {ownerName} 協助報名，需本人、協助報名人員或管理員才可取消')
            delUsers.append(user)

    for delUser in delUsers:
        list.remove(delUser)
        message += f'{delUser["userName"]} 取消報名場次{courtNo} \n'


    waitList = json.loads(r.hget(f'line-court:{groupId}:{courtNo}', 'waitList'))
    # 遞補候補清單
    if len(waitList) > 0:
        transList = waitList[0:len(delUsers)]
        list = list + transList
        waitList[0:len(delUsers)] = []

        for transUser in transList:
            message += f'，並由 {transUser["userName"]} 遞補 \n'
                

    # 將資料更新回redis
    r.hset(f'line-court:{groupId}:{courtNo}', 'list', json.dumps(list))
    r.hset(f'line-court:{groupId}:{courtNo}', 'waitList', json.dumps(waitList))
                    
    return message
    


def emptyList(r:Redis, groupId, courtNo):
    '''
        清空場次名單
    '''
    key = f'line-court:{groupId}:{courtNo}'
    if r.exists(key) == 0:
        raise ValueError(f'查無場次編號:{courtNo}，請重新確認')
    
    # 季打清單
    seasonList = r.hget(f'line-court:{groupId}:{courtNo}', 'seasonList')

    r.hset(f'line-court:{groupId}:{courtNo}', 'list', seasonList)
    r.hset(f'line-court:{groupId}:{courtNo}', 'waitList', '[]')


    return f'已清空場次 {courtNo} 的報名及候補清單並自動帶入季打清單'

def addSeasonList(r:Redis, line_bot_api, groupId, courtNo, addIds):
    '''
        新增季打名單
    '''
    key = f'line-court:{groupId}:{courtNo}'
    if r.exists(key) == 0:
        raise ValueError(f'查無場次編號:{courtNo}，請重新確認')
    
    if len(addIds) <= 0:
        raise ValueError(f'請使用tag方式標示出要新增進季打清單的成員')
    

    addNames = []
    users = []
    for userId in addIds:
        userName = getName(line_bot_api, groupId, userId)
        user = User(userId, userName)
        users.append(user)
        addNames.append(userName)

    newSeasonUsers = json.loads(json.dumps(users, default=lambda o: o.__dict__))
    seasonList = json.loads(r.hget(key, 'seasonList'))
    seasonList = seasonList + newSeasonUsers
    r.hset(key, 'seasonList', json.dumps(seasonList))

    return f'已將 {", ".join(addNames)} 新增至季打名單'

def removeSeasonList(r:Redis, line_bot_api, groupId, courtNo, delIds):
    '''
        移除季打名單
    '''
    key = f'line-court:{groupId}:{courtNo}'
    if r.exists(key) == 0:
        raise ValueError(f'查無場次編號:{courtNo}，請重新確認')
    
    if len(delIds) <= 0:
        raise ValueError(f'請使用tag方式標示出要移除季打清單的成員')
    
    seasonList = json.loads(r.hget(key, 'seasonList'))
    
    newList = [user for user in seasonList if user['userId'] not in delIds]
    r.hset(key, 'seasonList', json.dumps(newList, default=lambda o: o.__dict__))

    delNames = []

    for user in newList:
        if user['userId'] in delIds:
            delNames.append(user['userName'])

    return f'已將 {", ".join(delNames)} 移出季打名單'

def list(r:Redis, line_bot_api, groupId, courtNo):
    '''
        列出場次報名清單
    '''
    key = f'line-court:{groupId}:{courtNo}'
    if r.exists(key) == 0:
        raise ValueError(f'查無場次編號:{courtNo}，請重新確認')

    list = json.loads(r.hget(f'line-court:{groupId}:{courtNo}', 'list'))
    names = []
    message = ''
    for user in list:
        names.append(user['userName'])
    
    if len(names) > 0:
        message = f'報名清單：\n{", ".join(names)}'

    return message

def waitList(r:Redis, line_bot_api, groupId, courtNo):
    '''
        列出場次候補清單
    '''
    key = f'line-court:{groupId}:{courtNo}'
    if r.exists(key) == 0:
        raise ValueError(f'查無場次編號:{courtNo}，請重新確認')

    waitList = json.loads(r.hget(f'line-court:{groupId}:{courtNo}', 'waitList'))
    waitNames = []
    for user in waitList:
        waitNames.append(user['userName'])

    message = ''

    if len(waitNames) > 0:
        message = f'候補清單：\n{", ".join(waitNames)}'

    return message

def Seasonlist(r:Redis, line_bot_api, groupId, courtNo):
    '''
        列出場次季打清單
    '''
    key = f'line-court:{groupId}:{courtNo}'
    if r.exists(key) == 0:
        raise ValueError(f'查無場次編號:{courtNo}，請重新確認')

    list = json.loads(r.hget(f'line-court:{groupId}:{courtNo}', 'seasonList'))
    names = []
    message = ''
    for user in list:
        names.append(user['userName'])
    message = f'場次{courtNo} 季打名單：{", ".join(names)}'
    return message

def getName(line_bot_api, groupId, userId):
    try :
        name = line_bot_api.get_group_member_profile(groupId, userId).display_name
        return name
    except Exception:
        return userId
    
def getMentioneesOrError(event):
    try :
        mentionees = event.message.mention.mentionees
        return mentionees
    except Exception:
        raise ValueError(f'請使用 tag 方式標記成員')
    
def admin_func_card(r:Redis, groupId):
    
    carousel_contents = []

    # 場次資訊 Bubble
    courtBubble = BubbleContainer(
        hero=None,
        size='kilo',
        body=admin_court_body(r, groupId)
    )

    # 報名
    signUpBubble = BubbleContainer(
        hero=None,
        size='kilo',
        body=admin_user_body(r, groupId)
    )

    carousel_contents.append(courtBubble)
    carousel_contents.append(signUpBubble)

    contents = CarouselContainer(contents=carousel_contents)

    # 建立 FlexSendMessage 物件，將 BubbleContainer 放入其中
    message = FlexSendMessage(alt_text='管理員功能選單', contents=contents)
    return message    


def admin_user_body(r:Redis, groupId):
    box = BoxComponent(
        layout='vertical',
        contents=[
            TextComponent(
                text='人員維護',
                size='xl',
                weight='bold'
            ),
            TextComponent(
                text='部分管理員功能需手動輸入資料，請參考功能範例送出訊息',
                wrap=True
            ),
            SeparatorComponent(
                margin='15px'
            ),
            BoxComponent(
                layout='vertical',
                contents=[
                    TextComponent(
                        text='👉新增管理員',
                        size='lg',
                        margin='none',
                        flex=0,
                        weight='bold',
                    ),
                    TextComponent(
                        text='#新增管理員 @成員A @成員B',
                        size='sm',
                        weight='bold',
                        color='#FF2D2D',
                    ),
                    TextComponent(
                        text='用空白隔開，並確實標記到成員',
                        size='sm',
                        color='#999999',
                    ),
                    TextComponent(
                        text='⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️',
                        size='sm',
                        color='#999999',
                    ),
                    TextComponent(
                        text='#新增管理員 @小戴 @老天',
                        size='sm',
                        color='#00A600',
                    ),
                ]
            ),
            SeparatorComponent(
                margin='15px'
            ),
            BoxComponent(
                layout='vertical',
                contents=[
                    TextComponent(
                        text='👉移除管理員',
                        size='lg',
                        margin='none',
                        flex=0,
                        weight='bold',
                    ),
                    TextComponent(
                        text='#移除管理員 @成員A @成員B',
                        size='sm',
                        weight='bold',
                        color='#FF2D2D',
                    ),
                    TextComponent(
                        text='用空白隔開，並確實標記到成員',
                        size='sm',
                        color='#999999',
                    ),
                    TextComponent(
                        text='⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️',
                        size='sm',
                        color='#999999',
                    ),
                    TextComponent(
                        text='#移除管理員 @小戴 @老天',
                        size='sm',
                        color='#00A600',
                    ),
                ]
            ),
            SeparatorComponent(
                margin='15px'
            ),
            BoxComponent(
                layout='vertical',
                contents=[
                    TextComponent(
                        text='👉新增季打成員',
                        size='lg',
                        margin='none',
                        flex=0,
                        weight='bold',
                    ),
                    TextComponent(
                        text='#新增季打 場次代號 @成員A @成員B',
                        size='sm',
                        weight='bold',
                        color='#FF2D2D',
                    ),
                    TextComponent(
                        text='用空白隔開，並確實標記到成員',
                        size='sm',
                        color='#999999',
                    ),
                    TextComponent(
                        text='⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️',
                        size='sm',
                        color='#999999',
                    ),
                    TextComponent(
                        text='#新增季打 A @小戴 @老天',
                        size='sm',
                        color='#00A600',
                    ),
                ]
            ),
            SeparatorComponent(
                margin='15px'
            ),
            BoxComponent(
                layout='vertical',
                contents=[
                    TextComponent(
                        text='👉移除季打成員',
                        size='lg',
                        margin='none',
                        flex=0,
                        weight='bold',
                    ),
                    TextComponent(
                        text='#移除季打 場次代號 @成員A @成員B',
                        size='sm',
                        weight='bold',
                        color='#FF2D2D',
                    ),
                    TextComponent(
                        text='用空白隔開，並確實標記到成員',
                        size='sm',
                        color='#999999',
                    ),
                    TextComponent(
                        text='⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️',
                        size='sm',
                        color='#999999',
                    ),
                    TextComponent(
                        text='#移除季打 A @小戴 @老天',
                        size='sm',
                        color='#00A600',
                    ),
                ]
            ),
        ]
    )
    
    return box



def admin_court_body(r:Redis, groupId):
    box = BoxComponent(
        layout='vertical',
        contents=[
            TextComponent(
                text='場次維護',
                size='xl',
                weight='bold'
            ),
            SeparatorComponent(
                margin='15px'
            ),
            BoxComponent(
                layout='vertical',
                contents=[
                    TextComponent(
                        text='👉開場',
                        size='lg',
                        margin='none',
                        flex=0,
                        weight='bold',
                    ),
                    TextComponent(
                        text='開場需手動輸入資料，請參考範例送出訊息',
                        size='sm',
                        wrap=True
                    ),
                    TextComponent(
                        text='#開場 場次代號 日期 時間 地點 名額',
                        size='sm',
                        weight='bold',
                        color='#FF2D2D',
                    ),
                    TextComponent(
                        text='各個參數間用空白隔開',
                        size='sm',
                        color='#999999',
                    ),
                    TextComponent(
                        text='⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️ ⬇️',
                        size='sm',
                        color='#999999',
                    ),
                    TextComponent(
                        text='#開場 A 5/30 20-22 台北體育館 8',
                        size='sm',
                        color='#00A600',
                    ),
                    TextComponent(
                        text='⬆️ ⬆️ ⬆️ ⬆️ ⬆️ ⬆️ ⬆️ ⬆️ ⬆️',
                        size='sm',
                        color='#999999',
                    ),
                    TextComponent(
                        text='若有固定時間地點的場次，日期可以輸入每周一等字眼，開放報名前使用清空報名清單功能，就不用重新建立場次',
                        size='sm',
                        wrap=True,
                        color='#999999',
                    ),
                ]
            ),
            SeparatorComponent(
                margin='15px'
            ),
            BoxComponent(
                layout='vertical',
                contents=emptyBtn(r, groupId)
            ),
            SeparatorComponent(
                margin='15px'
            ),
            BoxComponent(
                layout='vertical',
                contents=delBtn(r, groupId)
            ),
        ]
    )
    
    return box


def func_card(r:Redis, groupId):
    
    carousel_contents = []

    # 場次資訊 Bubble
    infoBubble = BubbleContainer(
        hero=None,
        size='kilo',
        body=infoBody(r, groupId)
    )

    # 報名功能
    signUpBubble = BubbleContainer(
        hero=None,
        size='kilo',
        body=signBody(r, groupId)
    )

    carousel_contents.append(infoBubble)
    carousel_contents.append(signUpBubble)

    contents = CarouselContainer(contents=carousel_contents)

    # 建立 FlexSendMessage 物件，將 BubbleContainer 放入其中
    message = FlexSendMessage(alt_text='功能選單', contents=contents)
    return message    


def infoBody(r:Redis, groupId):
    box = BoxComponent(
        layout='vertical',
        contents=[
            BoxComponent(
                layout='vertical',
                contents=courtInfoContents(r, groupId)
            ),
            SeparatorComponent(
                margin='15px'
            ),
            BoxComponent(
                layout='vertical',
                contents=seasonContents(r, groupId)
            ),
            SeparatorComponent(
                margin='15px'
            ),
            BoxComponent(
                layout='vertical',
                contents=[
                    TextComponent(
                        text='👉管理員清單',
                        size='lg',
                        margin='none',
                        flex=0,
                        weight='bold',
                    ),
                    ButtonComponent(
                        action={
                            'type': 'message',
                            'label': f'管理員清單',
                            'text': f'#管理員清單'
                        }
                    )                         
                ]
            ),
        ]
    )
    
    return box



def emptyBtn(r:Redis, groupId):
    '''
        取消報名按鈕
    '''
    contents = [
        TextComponent(
            text='👉清空報名清單',
            size='lg',
            margin='none',
            flex=0,
            weight='bold',
        ),
        TextComponent(
            text='若有設定季打清單會自動代入',
            size='sm',
            wrap=True,
            color='#999999',
        )
    ]

    keys = getAllCourtNos(r, groupId)
    for courtNo in keys:
        buttonComponent = ButtonComponent(
            action={
                'type': 'message',
                'label': f'清空 {courtNo} 場',
                'text': f'#清空{courtNo}'
            }
        )     
        contents.append(buttonComponent)        



    return contents

def delBtn(r:Redis, groupId):
    '''
        取消報名按鈕
    '''
    contents = [
        TextComponent(
            text='👉刪除場次',
            size='lg',
            margin='none',
            flex=0,
            weight='bold',
        )
    ]

    keys = getAllCourtNos(r, groupId)
    for courtNo in keys:
        buttonComponent = ButtonComponent(
            action={
                'type': 'message',
                'label': f'刪除 {courtNo} 場',
                'text': f'#刪場{courtNo}'
            }
        )     
        contents.append(buttonComponent)        

    return contents




def signBody(r:Redis, groupId):
    '''
        我要報名按鈕
    '''
    box = BoxComponent(
        layout='vertical',
        contents=[
            BoxComponent(
                layout='vertical',
                contents=signUpContents(r, groupId)
            ),
            SeparatorComponent(
                margin='15px'
            ),
            BoxComponent(
                layout='vertical',
                contents=signOutContents(r, groupId)
            ),
        ]
    )
    return box


def signUpContents(r:Redis, groupId):
    '''
        我要報名按鈕
    '''
    contents = [
        TextComponent(
            text='👉馬上報名',
            size='lg',
            margin='none',
            flex=0,
            weight='bold',
        )
    ]

    keys = getAllCourtNos(r, groupId)
    for courtNo in keys:
        buttonComponent = ButtonComponent(
            action={
                'type': 'message',
                'label': f'我要報名場次 {courtNo}',
                'text': f'#{courtNo}'
            }
        )     
        contents.append(buttonComponent)        


    contents = contents + [
        TextComponent(
            text='若群組開放幫朋友報名，可參照格式手動輸入訊息',
            weight='bold',
            size='sm',
            wrap=True
        ),
        TextComponent(
            text='#代報 A 小戴 老天',
            size='sm',
            weight='bold',
            color='#FF2D2D',
        ),
        TextComponent(
            text='各個參數間用空白隔開',
            size='sm',
            color='#999999',
        )
    ]
    return contents



def signOutContents(r:Redis, groupId):
    '''
        取消報名按鈕
    '''
    contents = [
        TextComponent(
            text='👉取消報名',
            size='lg',
            margin='none',
            flex=0,
            weight='bold',
        )
    ]

    keys = getAllCourtNos(r, groupId)
    for courtNo in keys:
        buttonComponent = ButtonComponent(
            action={
                'type': 'message',
                'label': f'取消報名 {courtNo} 場次',
                'text': f'#取消{courtNo}'
            }
        )     
        contents.append(buttonComponent)        

    contents = contents + [
        TextComponent(
            text='若要幫代報的朋友取消報名，可參照格式手動輸入訊息',
            weight='bold',
            size='sm',
            wrap=True
        ),
        TextComponent(
            text='#取消 A 小戴 老天',
            size='sm',
            weight='bold',
            color='#FF2D2D',
        ),
        TextComponent(
            text='各個參數間用空白隔開',
            size='sm',
            color='#999999',
        )
    ]
    return contents


def courtInfoContents(r:Redis, groupId):
    '''
        場次清單按鈕
    '''
    contents = [
        TextComponent(
            text='👉場次資訊',
            size='lg',
            margin='none',
            flex=0,
            weight='bold',
        )
    ]

    keys = getAllCourtNos(r, groupId)
    for courtNo in keys:
        buttonComponent = ButtonComponent(
            action={
                'type': 'message',
                'label': f'場次{courtNo}資訊',
                'text': f'#場次資訊{courtNo}'
            }
        )     
        contents.append(buttonComponent)        



    return contents

def seasonContents(r:Redis, groupId):
    '''
        季打名單按鈕
    '''
    contents = [
        TextComponent(
            text='👉季打名單',
            size='lg',
            margin='none',
            flex=0,
            weight='bold',
        )
    ]
    keys = getAllCourtNos(r, groupId)
    for courtNo in keys:
        buttonComponent = ButtonComponent(
            action={
                'type': 'message',
                'label': f'場次 {courtNo} 季打名單',
                'text': f'#季打名單{courtNo}'
            }
        )     
        contents.append(buttonComponent)        

    return contents


def genHeaderBox(text):
    header = BoxComponent(
        layout='vertical',
        border_width='none',
        contents=[
            TextComponent(
                text=text,
                size='xl',
                align='center'
            ),
            SeparatorComponent()
        ]
    )
    return header
