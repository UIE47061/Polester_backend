from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from typing import Optional
from datetime import datetime
from functions.advertisements import AdvertisementService
from functions.image_generation import ImageGenerationService
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/advertisements",
    tags=["Advertisements"],
    responses={404: {"description": "Not found"}},
)


# ===== Pydantic 模型 =====

class AdvertisementResponse(BaseModel):
    """廣告回應模型"""
    id: Optional[int] = None
    image_url: str
    image_path: str
    description: str
    start_time: str
    end_time: str
    impression_count: int
    current_impressions: int = 0
    status: str = "active"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AdvertisementUpdateRequest(BaseModel):
    """廣告更新請求模型"""
    description: Optional[str] = Field(None, description="廣告敘述")
    start_time: Optional[datetime] = Field(None, description="投放開始時段")
    end_time: Optional[datetime] = Field(None, description="投放結束時段")
    impression_count: Optional[int] = Field(None, description="投放桿數量", ge=1)
    status: Optional[str] = Field(None, description="廣告狀態 (active, paused, completed)")


class ImageGenerationRequest(BaseModel):
    """圖片生成請求模型"""
    prompt: str = Field(..., description="圖片描述提示詞", min_length=1, max_length=1000)
    model: Optional[str] = Field("flux-schnell", description="使用的模型 (flux-schnell, sdxl, sd-1.5)")
    negative_prompt: Optional[str] = Field(None, description="負面提示詞（避免生成的內容）")


# ===== API 端點 =====

@router.post("/generate-image", summary="生成廣告圖片預覽", response_model=dict)
async def generate_image(request: ImageGenerationRequest = Body(...)):
    """
    使用 AI 生成廣告圖片（僅預覽，不儲存）
    
    - **prompt**: 圖片描述提示詞（例如：「一個美麗的海灘日落，專業攝影」）
    - **model**: 使用的模型，可選：
        - `flux-schnell` (推薦) - 速度快，品質優秀
        - `sdxl` - 高品質
        - `sd-1.5` - 經典模型
    - **negative_prompt**: 可選的負面提示詞（例如：「低品質，模糊」）
    
    回傳 base64 編碼的圖片，前端可直接顯示預覽。
    使用者確認後，可將此圖片用於建立廣告。
    """
    try:
        result = ImageGenerationService.generate_image(
            prompt=request.prompt,
            model=request.model,
            negative_prompt=request.negative_prompt
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])
        
        return {
            "success": True,
            "message": result["message"],
            "data": {
                "image_base64": result["data"]["image_base64"],
                "size": result["data"]["size"],
                "model": result["data"]["model"],
                "prompt": result["data"]["prompt"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成圖片時發生錯誤: {str(e)}")


@router.get("/models", summary="獲取可用的圖片生成模型", response_model=dict)
async def get_available_models():
    """
    獲取可用的 AI 圖片生成模型列表
    
    返回所有支援的模型及其描述
    """
    try:
        result = ImageGenerationService.get_available_models()
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取模型列表時發生錯誤: {str(e)}")


@router.post("/", summary="建立新廣告", response_model=dict)
async def create_advertisement(
    image: UploadFile = File(..., description="廣告圖片"),
    description: str = Form(..., description="廣告敘述"),
    start_time: str = Form(..., description="投放開始時段 (ISO 8601 格式，例: 2024-01-01T00:00:00)"),
    end_time: str = Form(..., description="投放結束時段 (ISO 8601 格式，例: 2024-12-31T23:59:59)"),
    impression_count: int = Form(..., description="投放桿數量", ge=1)
):
    """
    建立新廣告
    
    - **image**: 廣告圖片檔案
    - **description**: 廣告敘述文字
    - **start_time**: 投放開始時段 (ISO 8601 格式)
    - **end_time**: 投放結束時段 (ISO 8601 格式)
    - **impression_count**: 投放桿數量 (必須 >= 1)
    """
    try:
        # 驗證圖片類型
        if not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="只接受圖片檔案")
        
        # 驗證圖片大小 (限制 10MB)
        contents = await image.read()
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="圖片大小不能超過 10MB")
        
        # 解析時間
        try:
            start_datetime = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_datetime = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="時間格式錯誤，請使用 ISO 8601 格式 (例: 2024-01-01T00:00:00)"
            )
        
        # 驗證時間邏輯
        if end_datetime <= start_datetime:
            raise HTTPException(status_code=400, detail="結束時間必須晚於開始時間")
        
        # 建立廣告
        result = await AdvertisementService.create_advertisement(
            image_data=contents,
            image_filename=image.filename,
            description=description,
            start_time=start_datetime,
            end_time=end_datetime,
            impression_count=impression_count
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])
        
        return JSONResponse(
            status_code=201,
            content={
                "success": True,
                "message": result["message"],
                "data": result["data"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"建立廣告時發生錯誤: {str(e)}")


@router.get("/", summary="獲取廣告列表", response_model=dict)
async def get_advertisements(
    status: Optional[str] = Query(None, description="廣告狀態篩選 (active, paused, completed)"),
    limit: int = Query(100, description="返回數量限制", ge=1, le=1000),
    offset: int = Query(0, description="偏移量", ge=0)
):
    """
    獲取廣告列表
    
    - **status**: 可選的狀態篩選 (active, paused, completed)
    - **limit**: 返回數量限制 (1-1000)
    - **offset**: 偏移量，用於分頁
    """
    try:
        result = await AdvertisementService.get_all_advertisements(
            status=status,
            limit=limit,
            offset=offset
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])
        
        return {
            "success": True,
            "message": result["message"],
            "data": result["data"],
            "count": result["count"],
            "limit": limit,
            "offset": offset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取廣告列表時發生錯誤: {str(e)}")


@router.get("/active", summary="獲取有效廣告", response_model=dict)
async def get_active_advertisements():
    """
    獲取所有狀態為 active 的廣告
    
    只返回狀態為 active 的廣告
    """
    try:
        result = await AdvertisementService.get_active_advertisements()
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])
        
        return {
            "success": True,
            "message": result["message"],
            "data": result["data"],
            "count": result["count"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取有效廣告時發生錯誤: {str(e)}")


@router.get("/{ad_id}", summary="獲取單一廣告", response_model=dict)
async def get_advertisement(ad_id: int):
    """
    根據 ID 獲取單一廣告詳細資訊
    
    - **ad_id**: 廣告 ID
    """
    try:
        result = await AdvertisementService.get_advertisement(ad_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])
        
        return {
            "success": True,
            "message": result["message"],
            "data": result["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取廣告時發生錯誤: {str(e)}")


@router.patch("/{ad_id}", summary="更新廣告", response_model=dict)
async def update_advertisement(ad_id: int, update_data: AdvertisementUpdateRequest):
    """
    更新廣告資訊
    
    - **ad_id**: 廣告 ID
    - **update_data**: 要更新的欄位（可選）
    """
    try:
        result = await AdvertisementService.update_advertisement(
            ad_id=ad_id,
            description=update_data.description,
            start_time=update_data.start_time,
            end_time=update_data.end_time,
            impression_count=update_data.impression_count,
            status=update_data.status
        )
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])
        
        return {
            "success": True,
            "message": result["message"],
            "data": result["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新廣告時發生錯誤: {str(e)}")


@router.post("/{ad_id}/impression", summary="增加廣告曝光次數", response_model=dict)
async def increment_impression(ad_id: int):
    """
    增加廣告的曝光次數
    
    - **ad_id**: 廣告 ID
    
    當曝光次數達到目標投放桿數時，會自動將狀態更新為 completed
    """
    try:
        result = await AdvertisementService.increment_impression(ad_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])
        
        return {
            "success": True,
            "message": result["message"],
            "data": result["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新曝光次數時發生錯誤: {str(e)}")


@router.delete("/{ad_id}", summary="刪除廣告", response_model=dict)
async def delete_advertisement(ad_id: int):
    """
    刪除廣告
    
    - **ad_id**: 廣告 ID
    
    會同時刪除 Supabase Storage 中的圖片和資料庫中的記錄
    """
    try:
        result = await AdvertisementService.delete_advertisement(ad_id)
        
        if not result["success"]:
            raise HTTPException(status_code=404, detail=result["message"])
        
        return {
            "success": True,
            "message": result["message"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刪除廣告時發生錯誤: {str(e)}")
