# Polester Backend API

Polester 後端 API 服務，提供廣告刊登與管理功能。

## 📋 專案簡介

這是一個基於 FastAPI 開發的後端 API 服務，整合 Supabase 作為資料庫與檔案儲存解決方案。主要功能包括廣告的建立、查詢、更新、刪除以及曝光追蹤。

### 主要功能

- 📸 **廣告圖片上傳** - 支援圖片上傳至 Supabase Storage
- 📝 **廣告資訊管理** - 完整的 CRUD 操作
- ⏰ **時段控制** - 設定廣告投放的開始與結束時間
- 📊 **曝光追蹤** - 記錄與統計廣告曝光次數
- 🎯 **智能篩選** - 自動篩選有效廣告（時段內且未達曝光上限）

## 🛠️ 技術架構

- **框架**: FastAPI
- **資料庫**: Supabase (PostgreSQL)
- **檔案儲存**: Supabase Storage
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
│   └── advertisements.py  # 廣告業務邏輯
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

# API 文件認證
DOCS_USERNAME=admin
DOCS_PASSWORD=your_password

# 伺服器設定
PORT=7860
RELOAD=true
```

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

#### 1. 建立廣告

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

#### 2. 獲取廣告列表

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

#### 3. 獲取有效廣告

**GET** `/advertisements/active`

返回符合以下條件的廣告：
- 狀態為 `active`
- 當前時間在投放時段內
- 曝光次數未達到目標

**範例**:

```javascript
const response = await fetch('http://localhost:7860/advertisements/active');
const result = await response.json();
```

#### 4. 獲取單一廣告

**GET** `/advertisements/{ad_id}`

**範例**:

```javascript
const response = await fetch('http://localhost:7860/advertisements/1');
const result = await response.json();
```

#### 5. 更新廣告

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

#### 6. 增加曝光次數

**POST** `/advertisements/{ad_id}/impression`

用於記錄廣告被顯示的次數。當曝光次數達到設定的 `impression_count` 時，狀態會自動更新為 `completed`。

**範例**:

```javascript
const response = await fetch('http://localhost:7860/advertisements/1/impression', {
    method: 'POST'
});
```

#### 7. 刪除廣告

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

## 🐛 常見問題

### 1. Bucket not found 錯誤

如果遇到儲存桶不存在的錯誤，請確認：
- 使用的是 **Service Role Key**，而非 Anon Key
- Supabase Storage 功能已啟用
- 程式會在首次上傳時自動建立儲存桶

### 2. 圖片上傳失敗

檢查事項：
- 圖片大小是否超過 10MB
- 檔案格式是否為圖片類型
- Supabase Storage 配額是否已滿

### 3. 時間格式錯誤

時間格式必須符合 ISO 8601 標準：
- 正確: `2024-01-01T00:00:00`
- 正確: `2024-01-01T00:00:00Z`
- 正確: `2024-01-01T00:00:00+08:00`

