# Polester Backend API

Polester 後端 API 服務，提供廣告刊登、管理與 AI 圖片生成功能。

## 📋 專案簡介

這是一個基於 FastAPI 開發的後端 API 服務，整合 Supabase 作為資料庫與檔案儲存解決方案，並串接 Hugging Face AI 模型提供圖片生成功能。主要功能包括廣告的建立、查詢、更新、刪除、曝光追蹤，以及 AI 輔助生成廣告圖片。

### 主要功能

- 🎨 **AI 圖片生成** - 使用 Hugging Face 模型生成廣告圖片
- 📸 **廣告圖片上傳** - 支援圖片上傳至 Supabase Storage
- 📝 **廣告資訊管理** - 完整的 CRUD 操作
- ⏰ **時段控制** - 設定廣告投放的開始與結束時間
- 📊 **曝光追蹤** - 記錄與統計廣告曝光次數
- 🎯 **智能篩選** - 自動篩選有效廣告

## 🛠️ 技術架構

- **框架**: FastAPI
- **資料庫**: Supabase (PostgreSQL)
- **檔案儲存**: Supabase Storage
- **AI 模型**: Hugging Face (FLUX.1, Stable Diffusion)
- **伺服器**: Uvicorn
- **環境管理**: python-dotenv

## 📁 專案結構

```
Polester_backend/
├── app.py              # 主應用程式入口
├── requirements.txt    # Python 套件依賴
├── .env               # 環境變數配置（需自行建立）
├── util/
│   └── config.py      # 環境變數管理
├── functions/
│   ├── advertisements.py    # 廣告業務邏輯
│   └── image_generation.py  # AI 圖片生成服務
└── router/
    └── advertisements.py  # 廣告 API 路由
```

## 🚀 快速開始

### 1. 環境需求

- Python 3.8+
- Supabase 帳號（需要 URL 和 Service Role Key）

### 2. 安裝套件

```bash
pip install -r requirements.txt
```

### 3. 環境變數設定

在專案根目錄建立 `.env` 檔案：

```env
# Supabase 設定
SUPABASE_URL=你的_supabase_專案_url
SUPABASE_KEY=你的_supabase_service_role_key

# Hugging Face 設定（用於 AI 圖片生成）
HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxxxxxxxx

# API 文件認證
DOCS_USERNAME=admin
DOCS_PASSWORD=your_password

# 伺服器設定
PORT=7860
RELOAD=true
```

**取得 Hugging Face Token**:
1. 註冊 https://huggingface.co/
2. 前往 Settings → Access Tokens
3. 建立新的 token（選擇 **Read** 權限即可）
4. 複製 token 並加入 `.env`

### 4. Supabase 資料庫設定

在 Supabase SQL Editor 執行以下 SQL 建立資料表：

```sql
CREATE TABLE advertisements (
    id BIGSERIAL PRIMARY KEY,
    image_url TEXT NOT NULL,
    image_path TEXT NOT NULL,
    description TEXT NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    impression_count INTEGER NOT NULL,
    current_impressions INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- 建立索引以提升查詢效能
CREATE INDEX idx_advertisements_status ON advertisements(status);
CREATE INDEX idx_advertisements_time_range ON advertisements(start_time, end_time);
```

**注意**：Storage Bucket 會在首次上傳時自動建立，無需手動設定。

### 5. 啟動服務

```bash
python app.py
```

或使用 uvicorn：

```bash
uvicorn app:app --host 0.0.0.0 --port 7860 --reload
```

服務啟動後可訪問：
- API 文件: `http://localhost:7860/docs`
- 健康檢查: `http://localhost:7860/health`

## 📚 API 使用說明

### 基礎 URL

```
http://localhost:7860
```

### API 端點

#### 1. AI 生成廣告圖片（預覽）

**POST** `/advertisements/generate-image`

使用 AI 生成廣告圖片，返回 base64 編碼的圖片供前端預覽。

**請求 Body**:

```json
{
    "prompt": "a beautiful sunset over the ocean, professional photography",
    "model": "flux-schnell",
    "negative_prompt": "low quality, blurry"
}
```

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| prompt | String | ✅ | 圖片描述提示詞（1-1000字） |
| model | String | ❌ | 模型選擇（預設: flux-schnell） |
| negative_prompt | String | ❌ | 負面提示詞（避免生成的內容） |

**可用模型**:
- `flux-schnell` (推薦) - 速度快，品質優秀
- `sdxl` - 高品質 Stable Diffusion XL
- `sd-1.5` - 經典 Stable Diffusion 1.5

**範例**:

```javascript
const response = await fetch('http://localhost:7860/advertisements/generate-image', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        prompt: '一個美麗的海灘日落，專業攝影',
        model: 'flux-schnell'
    })
});

const result = await response.json();
// 顯示預覽
const img = document.createElement('img');
img.src = `data:image/png;base64,${result.data.image_base64}`;
document.body.appendChild(img);
```

**回應**:

```json
{
    "success": true,
    "message": "圖片生成成功",
    "data": {
        "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
        "size": 96504,
        "model": "flux-schnell",
        "prompt": "一個美麗的海灘日落，專業攝影"
    }
}
```

**使用流程**:
1. 前端呼叫此 API 生成圖片預覽
2. 使用者確認圖片後，將 base64 轉為 File
3. 使用下方「建立廣告」API 上傳確認的圖片

```javascript
// 將 base64 轉為 File
const blob = await fetch(`data:image/png;base64,${base64}`).then(r => r.blob());
const file = new File([blob], 'generated-ad.png', {type: 'image/png'});

// 上傳建立廣告（使用下方 API）
const formData = new FormData();
formData.append('image', file);
// ... 其他參數
```

#### 2. 獲取可用的 AI 模型

**GET** `/advertisements/models`

獲取所有支援的 AI 圖片生成模型列表。

**範例**:

```javascript
const response = await fetch('http://localhost:7860/advertisements/models');
const result = await response.json();
```

**回應**:

```json
{
    "success": true,
    "data": {
        "models": [
            {
                "id": "flux-schnell",
                "name": "FLUX.1 Schnell",
                "description": "速度快，品質優秀，推薦使用",
                "recommended": true
            },
            {
                "id": "sdxl",
                "name": "Stable Diffusion XL",
                "description": "高品質圖片生成",
                "recommended": false
            }
        ],
        "default": "flux-schnell"
    }
}
```

#### 3. 建立廣告

**POST** `/advertisements/`

使用 `multipart/form-data` 上傳資料。

**請求參數**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| image | File | ✅ | 廣告圖片（最大 10MB） |
| description | String | ✅ | 廣告敘述 |
| start_time | String | ✅ | 投放開始時間（ISO 8601 格式） |
| end_time | String | ✅ | 投放結束時間（ISO 8601 格式） |
| impression_count | Integer | ✅ | 投放桿數量（>= 1） |

**範例**:

```javascript
const formData = new FormData();
formData.append('image', imageFile);
formData.append('description', '2024 新年促銷活動');
formData.append('start_time', '2024-01-01T00:00:00');
formData.append('end_time', '2024-01-31T23:59:59');
formData.append('impression_count', 1000);

const response = await fetch('http://localhost:7860/advertisements/', {
    method: 'POST',
    body: formData
});

const result = await response.json();
console.log(result);
```

**回應**:

```json
{
    "success": true,
    "message": "廣告建立成功",
    "data": {
        "id": 1,
        "image_url": "https://...",
        "description": "2024 新年促銷活動",
        "start_time": "2024-01-01T00:00:00",
        "end_time": "2024-01-31T23:59:59",
        "impression_count": 1000,
        "current_impressions": 0,
        "status": "active",
        "created_at": "2024-01-01T10:00:00"
    }
}
```

#### 4. 獲取廣告列表

**GET** `/advertisements/`

**查詢參數**:

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| status | String | ❌ | 狀態篩選 (active/paused/completed) |
| limit | Integer | ❌ | 返回數量（預設 100，最大 1000） |
| offset | Integer | ❌ | 偏移量（用於分頁，預設 0） |

**範例**:

```javascript
// 獲取所有啟用中的廣告
const response = await fetch('http://localhost:7860/advertisements/?status=active&limit=10');
const result = await response.json();
```

#### 5. 獲取有效廣告

**GET** `/advertisements/active`

返回所有狀態為 `active` 的廣告。

**範例**:

```javascript
const response = await fetch('http://localhost:7860/advertisements/active');
const result = await response.json();
```

#### 6. 獲取單一廣告

**GET** `/advertisements/{ad_id}`

**範例**:

```javascript
const response = await fetch('http://localhost:7860/advertisements/1');
const result = await response.json();
```

#### 7. 更新廣告

**PATCH** `/advertisements/{ad_id}`

**請求 Body**:

```json
{
    "description": "更新後的廣告敘述",
    "start_time": "2024-02-01T00:00:00",
    "end_time": "2024-02-28T23:59:59",
    "impression_count": 2000,
    "status": "paused"
}
```

所有欄位皆為選填，只更新提供的欄位。

**範例**:

```javascript
const response = await fetch('http://localhost:7860/advertisements/1', {
    method: 'PATCH',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        status: 'paused'
    })
});
```

#### 8. 增加曝光次數

**POST** `/advertisements/{ad_id}/impression`

用於記錄廣告被顯示的次數。當曝光次數達到設定的 `impression_count` 時，狀態會自動更新為 `completed`。

**範例**:

```javascript
const response = await fetch('http://localhost:7860/advertisements/1/impression', {
    method: 'POST'
});
```

#### 9. 刪除廣告

**DELETE** `/advertisements/{ad_id}`

會同時刪除資料庫記錄和 Storage 中的圖片。

**範例**:

```javascript
const response = await fetch('http://localhost:7860/advertisements/1', {
    method: 'DELETE'
});
```

## 📊 廣告狀態說明

| 狀態 | 說明 |
|------|------|
| `active` | 啟用中，可正常顯示 |
| `paused` | 已暫停，不會顯示 |
| `completed` | 已完成（達到曝光上限） |

## 🔒 API 文件認證

訪問 `/docs` 或 `/redoc` 時需要提供帳號密碼：
- 帳號密碼在 `.env` 中的 `DOCS_USERNAME` 和 `DOCS_PASSWORD` 設定