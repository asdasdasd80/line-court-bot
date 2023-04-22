# LINE 群組揪團報名小幫手
此聊天機器人可協助管理打球開場及報名的流程，降低主揪的工作量，簡化用戶報名流程
## 如何使用 

1. 前往[LINE developers conlose](https://developers.line.biz/console)申請 Providers 並建立 Channel，取得 `Access Token` 以及 `Channel Secret`

2. Clone Source Code，並將 Access Token 以及 Channel Secret 輸入到 `app/config/config.py` 裡

3. 需要一個 `Redis Server` 充當資料庫，並將 `host` 以及 `port` 也輸入到 `app/config/config.py` 裡

4. 安裝 python 3.8，將終端機切換到專案目錄下，執行 `pip install -r requirements.txt`，安裝所需套件

5. 執行 `python app/main.py` 開啟服務
   
6. 設定 LINE developers conlose `webhook` 的服務網址，注意需使用 `https`

## 功能清單
所有指令都使用 `#` 開頭，參數間都以 `空格` 隔開

### 顯示功能列表的指令
因為有使用 Flex Message 模板，大部分指令都有做按鈕讓使用者直接點選，少數需要使用者手動輸入參數的功能，如輸入開場資訊、指定用戶等功能才需手動輸入指令，可使用下面兩個指令在群組內顯示所有功能項

1. 功能清單：顯示一般使用者可使用的功能清單  
   指令：`#功能`
2. 管理員功能清單：顯示管理員權限可使用的功能清單  
   指令：`#管理員功能`

### 管理員權限才能使用的功能清單
1. 註冊群組：初始化群組資訊，將`群組名稱`、`group_id` 記錄到 `Redis`裡，並`將執行此功能的用戶設定為群組管理員`  
指令：`#註冊群組`

2. 新增管理員：將群組內用戶設定為管理員，協助處理開團事務，用戶名稱需使用 `@` 標記群組內用戶，若一次要新增多個管理員，使用`空格`隔開  
指令：`#新增管理員 @用戶A @用戶B`
3. 移除管理員：將群組內用戶的管理員權限移除，本工具並無審核機制，只要是管理員都可以執行此功能，請群組自行管控使用時機  
指令：`#移除管理員 @用戶A @用戶B`
4. 開場：需依序填入`場次代號`、`日期`、`時間`、`地點`、`開放人數`等資訊，場次代號建議使用英文 A ~ Z  
指令：`#開場 場次代號 日期 時間 地點 開放人數`  
範例：`#開場 A 4/30 20-22 台北體育館 8`  
如果有固定的場次，日期可改為使用`每周幾`的字眼  
例如：`#開場 A 每周六 18-20 台北體育館 8`  
這樣就不需每周重新輸入，僅需要在開放報名時使用`清空報名名單功能`即可  
5. 刪除場次：輸入場次代號來刪除場次資料，不支援一次輸入多個代號  
指令：`#刪場 場次代號`
6. 清空名單：輸入場次代號，將指定場次的報名清單、候補清單都清空，並自動代入該場次季打清單
指令：`#清空 場次代號` 
7. 新增季打名單：可以為場次設定季打名單，在使用清空名單時會自動代入季打名單，注意新增季打名單需要使用 `@` 方式標記用戶，支援同時輸入多個用戶  
指令：`#新增季打 場次代號 @用戶A @用戶B`
8. 將用戶移出季打名單：同樣需要使用 `@` 方式標記用戶，支援同時輸入多個用戶  
指令：`#移除季打 場次代號 @用戶A @用戶B`

### 所有用戶都可使用的功能清單
1. 場次資訊：查看群組內的所有開場，包含時間、地點報名/候補名單等資訊  
指令：`#場次資訊 場次代號`，如 `#場次資訊 A`
2. 報名：若僅幫自己報名，使用下面指令即可  
指令：`#場次代號`，例如 `#A`
3. 幫朋友報名：若群組開放幫非群內朋友報名，使用下面指令  
指令：`#代報 場次代號 友一 友二`，如 `#代報 A 阿貓 阿狗`
4. 取消報名：取消自己的報名  
指令：`#取消 場次代號`，如`#取消 A`
若要幫代報的朋友取消報名，將代報改為取消即可，一般用戶僅可取消代報友人，管理員有權限可以取消任意用戶  
指令：`#取消 場次代號 友一 友二`，如 `#取消 A 阿貓 阿狗`
5. 季打名單：顯示特定場次的季打名單  
指令：`#季打名單 場次代號`
6. 管理員名單：顯示所有管理員  
指令：`#管理員清單`

   
