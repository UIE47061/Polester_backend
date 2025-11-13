from supabase import create_client, Client
from util.config import env
from typing import Optional
from datetime import datetime
import uuid

# 儲存桶名稱
STORAGE_BUCKET = "advertisements"

# Supabase 客戶端（延遲初始化）
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """獲取 Supabase 客戶端（延遲初始化）"""
    global _supabase_client
    if _supabase_client is None:
        if not env.SUPABASE_URL or not env.SUPABASE_KEY:
            raise ValueError("SUPABASE_URL 和 SUPABASE_KEY 環境變數必須設定")
        _supabase_client = create_client(env.SUPABASE_URL, env.SUPABASE_KEY)
    return _supabase_client


def ensure_bucket_exists():
    """確保 Storage Bucket 存在，如果不存在則建立"""
    try:
        supabase = get_supabase_client()
        # 嘗試列出所有桶
        buckets = supabase.storage.list_buckets()
        bucket_names = [bucket.name for bucket in buckets]
        
        # 如果桶不存在，則建立
        if STORAGE_BUCKET not in bucket_names:
            supabase.storage.create_bucket(
                STORAGE_BUCKET,
                options={"public": True}
            )
            print(f"已建立儲存桶: {STORAGE_BUCKET}")
    except Exception as e:
        print(f"檢查或建立儲存桶時發生錯誤: {e}")


class AdvertisementService:
    """廣告服務類別，處理廣告的 CRUD 操作"""
    
    @staticmethod
    async def create_advertisement(
        image_data: bytes,
        image_filename: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
        impression_count: int
    ) -> dict:
        """
        建立新廣告
        
        Args:
            image_data: 圖片的二進制資料
            image_filename: 圖片檔案名稱
            description: 廣告敘述
            start_time: 投放開始時段
            end_time: 投放結束時段
            impression_count: 投放桿數量
            
        Returns:
            建立的廣告資料
        """
        try:
            # 確保儲存桶存在
            ensure_bucket_exists()
            
            supabase = get_supabase_client()
            
            # 生成唯一的檔案名稱
            file_extension = image_filename.split('.')[-1]
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            storage_path = f"advertisements/{unique_filename}"
            
            # 上傳圖片到 Supabase Storage
            upload_response = supabase.storage.from_(STORAGE_BUCKET).upload(
                path=storage_path,
                file=image_data,
                file_options={"content-type": f"image/{file_extension}"}
            )
            
            # 獲取公開 URL
            image_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)
            
            # 將廣告資料存入資料庫
            advertisement_data = {
                "image_url": image_url,
                "image_path": storage_path,
                "description": description,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "impression_count": impression_count,
                "current_impressions": 0,
                "status": "active",
                "created_at": datetime.now().isoformat()
            }
            
            response = supabase.table("advertisements").insert(advertisement_data).execute()
            
            return {
                "success": True,
                "data": response.data[0] if response.data else None,
                "message": "廣告建立成功"
            }
            
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "message": f"建立廣告失敗: {str(e)}"
            }
    
    @staticmethod
    async def get_advertisement(ad_id: int) -> dict:
        """
        獲取單一廣告
        
        Args:
            ad_id: 廣告 ID
            
        Returns:
            廣告資料
        """
        try:
            supabase = get_supabase_client()
            response = supabase.table("advertisements").select("*").eq("id", ad_id).execute()
            
            if not response.data:
                return {
                    "success": False,
                    "data": None,
                    "message": "找不到該廣告"
                }
            
            return {
                "success": True,
                "data": response.data[0],
                "message": "獲取廣告成功"
            }
            
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "message": f"獲取廣告失敗: {str(e)}"
            }
    
    @staticmethod
    async def get_all_advertisements(
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> dict:
        """
        獲取所有廣告列表
        
        Args:
            status: 廣告狀態篩選 (active, paused, completed)
            limit: 返回數量限制
            offset: 偏移量
            
        Returns:
            廣告列表
        """
        try:
            supabase = get_supabase_client()
            query = supabase.table("advertisements").select("*")
            
            if status:
                query = query.eq("status", status)
            
            response = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
            
            return {
                "success": True,
                "data": response.data,
                "count": len(response.data),
                "message": "獲取廣告列表成功"
            }
            
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "message": f"獲取廣告列表失敗: {str(e)}"
            }
    
    @staticmethod
    async def get_active_advertisements() -> dict:
        """
        獲取所有狀態為 active 的廣告
        
        Returns:
            有效廣告列表
        """
        try:
            supabase = get_supabase_client()
            response = (
                supabase.table("advertisements")
                .select("*")
                .eq("status", "active")
                .order("created_at", desc=True)
                .execute()
            )
            
            return {
                "success": True,
                "data": response.data,
                "count": len(response.data),
                "message": "獲取有效廣告成功"
            }
            
        except Exception as e:
            return {
                "success": False,
                "data": [],
                "message": f"獲取有效廣告失敗: {str(e)}"
            }
    
    @staticmethod
    async def update_advertisement(
        ad_id: int,
        description: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        impression_count: Optional[int] = None,
        status: Optional[str] = None
    ) -> dict:
        """
        更新廣告資訊
        
        Args:
            ad_id: 廣告 ID
            description: 廣告敘述
            start_time: 投放開始時段
            end_time: 投放結束時段
            impression_count: 投放桿數量
            status: 廣告狀態
            
        Returns:
            更新後的廣告資料
        """
        try:
            update_data = {}
            
            if description is not None:
                update_data["description"] = description
            if start_time is not None:
                update_data["start_time"] = start_time.isoformat()
            if end_time is not None:
                update_data["end_time"] = end_time.isoformat()
            if impression_count is not None:
                update_data["impression_count"] = impression_count
            if status is not None:
                update_data["status"] = status
            
            if not update_data:
                return {
                    "success": False,
                    "data": None,
                    "message": "沒有提供更新資料"
                }
            
            update_data["updated_at"] = datetime.now().isoformat()
            
            supabase = get_supabase_client()
            response = (
                supabase.table("advertisements")
                .update(update_data)
                .eq("id", ad_id)
                .execute()
            )
            
            if not response.data:
                return {
                    "success": False,
                    "data": None,
                    "message": "找不到該廣告"
                }
            
            return {
                "success": True,
                "data": response.data[0],
                "message": "廣告更新成功"
            }
            
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "message": f"更新廣告失敗: {str(e)}"
            }
    
    @staticmethod
    async def increment_impression(ad_id: int) -> dict:
        """
        增加廣告曝光次數
        
        Args:
            ad_id: 廣告 ID
            
        Returns:
            更新結果
        """
        try:
            # 先獲取當前的曝光次數
            ad_response = await AdvertisementService.get_advertisement(ad_id)
            
            if not ad_response["success"]:
                return ad_response
            
            ad_data = ad_response["data"]
            current_impressions = ad_data.get("current_impressions", 0)
            impression_count = ad_data.get("impression_count", 0)
            
            # 增加曝光次數
            new_impressions = current_impressions + 1
            
            # 如果達到目標曝光數，更新狀態為 completed
            update_data = {"current_impressions": new_impressions}
            if new_impressions >= impression_count:
                update_data["status"] = "completed"
            
            supabase = get_supabase_client()
            response = (
                supabase.table("advertisements")
                .update(update_data)
                .eq("id", ad_id)
                .execute()
            )
            
            return {
                "success": True,
                "data": response.data[0] if response.data else None,
                "message": "曝光次數更新成功"
            }
            
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "message": f"更新曝光次數失敗: {str(e)}"
            }
    
    @staticmethod
    async def delete_advertisement(ad_id: int) -> dict:
        """
        刪除廣告（同時刪除 Storage 中的圖片）
        
        Args:
            ad_id: 廣告 ID
            
        Returns:
            刪除結果
        """
        try:
            # 先獲取廣告資料以取得圖片路徑
            ad_response = await AdvertisementService.get_advertisement(ad_id)
            
            if not ad_response["success"]:
                return ad_response
            
            ad_data = ad_response["data"]
            image_path = ad_data.get("image_path")
            
            supabase = get_supabase_client()
            
            # 從 Storage 刪除圖片
            if image_path:
                try:
                    supabase.storage.from_(STORAGE_BUCKET).remove([image_path])
                except Exception as storage_error:
                    print(f"刪除圖片失敗: {storage_error}")
            
            # 從資料庫刪除廣告記錄
            response = supabase.table("advertisements").delete().eq("id", ad_id).execute()
            
            return {
                "success": True,
                "data": None,
                "message": "廣告刪除成功"
            }
            
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "message": f"刪除廣告失敗: {str(e)}"
            }
