import requests
import base64
import re
from util.config import env
from typing import Optional, Dict
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class ImageGenerationService:
    """圖片生成服務，使用 Hugging Face Inference API"""
    
    # 可用的模型列表
    MODELS = {
        "flux-schnell": "black-forest-labs/FLUX.1-schnell",  # 快速，品質好
        "sdxl": "stabilityai/stable-diffusion-xl-base-1.0",  # 高品質
        "sd-1.5": "runwayml/stable-diffusion-v1-5"  # 經典
    }
    
    DEFAULT_MODEL = "flux-schnell"
    
    @staticmethod
    def _contains_chinese(text: str) -> bool:
        """檢查文字是否包含中文字元"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    @staticmethod
    def _translate_to_english(text: str) -> str:
        """將中文翻譯成英文"""
        try:
            if not GEMINI_AVAILABLE:
                return text
            
            if not env.GEMINI_API_KEY:
                print("警告: GEMINI_API_KEY 未設定，無法翻譯中文提示詞")
                return text
            
            # 設定 Gemini API
            genai.configure(api_key=env.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-pro')
            
            # 翻譯提示詞
            prompt = f"""請將以下中文文字翻譯成英文，用於 AI 圖片生成。
                    只需要回傳翻譯結果，不要有其他說明文字。
                    保持描述的細節和風格。

                    中文: {text}
                    英文:"""
            
            response = model.generate_content(prompt)
            translated = response.text.strip()
            
            print(f"翻譯: {text} -> {translated}")
            return translated
            
        except Exception as e:
            print(f"翻譯失敗: {e}，使用原始提示詞")
            return text
    
    @staticmethod
    def generate_image(
        prompt: str,
        model: str = DEFAULT_MODEL,
        negative_prompt: Optional[str] = None
    ) -> Dict:
        """
        生成圖片
        
        Args:
            prompt: 圖片描述提示詞
            model: 使用的模型 (flux-schnell, sdxl, sd-1.5)
            negative_prompt: 負面提示詞（避免生成的內容）
            
        Returns:
            包含 success, data (base64圖片), message 的字典
        """
        try:
            # 檢查 token
            if not env.HUGGINGFACE_TOKEN:
                return {
                    "success": False,
                    "data": None,
                    "message": "HUGGINGFACE_TOKEN 環境變數未設定"
                }
            
            # 檢查並翻譯中文提示詞
            original_prompt = prompt
            if ImageGenerationService._contains_chinese(prompt):
                prompt = ImageGenerationService._translate_to_english(prompt)
            
            # 翻譯負面提示詞（如果有）
            if negative_prompt and ImageGenerationService._contains_chinese(negative_prompt):
                negative_prompt = ImageGenerationService._translate_to_english(negative_prompt)
            
            # 獲取模型 URL
            model_id = ImageGenerationService.MODELS.get(model)
            if not model_id:
                return {
                    "success": False,
                    "data": None,
                    "message": f"不支援的模型: {model}，可用模型: {list(ImageGenerationService.MODELS.keys())}"
                }
            
            # API 端點
            api_url = f"https://router.huggingface.co/hf-inference/models/{model_id}"
            headers = {"Authorization": f"Bearer {env.HUGGINGFACE_TOKEN}"}
            
            # 準備請求參數
            payload = {"inputs": prompt}
            if negative_prompt:
                payload["negative_prompt"] = negative_prompt
            
            # 發送請求
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=60  # 60秒超時
            )
            
            # 檢查回應
            if response.status_code == 200:
                # 將圖片轉為 base64
                image_bytes = response.content
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                
                return {
                    "success": True,
                    "data": {
                        "image_base64": image_base64,
                        "image_bytes": image_bytes,
                        "size": len(image_bytes),
                        "model": model,
                        "prompt": prompt,
                        "original_prompt": original_prompt
                    },
                    "message": "圖片生成成功"
                }
            
            elif response.status_code == 503:
                return {
                    "success": False,
                    "data": None,
                    "message": "模型正在載入中，請稍後再試（約需要 20-30 秒）"
                }
            
            else:
                error_msg = response.text
                return {
                    "success": False,
                    "data": None,
                    "message": f"圖片生成失敗 (HTTP {response.status_code}): {error_msg}"
                }
                
        except requests.Timeout:
            return {
                "success": False,
                "data": None,
                "message": "請求超時，模型可能需要更長時間載入，請稍後再試"
            }
        
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "message": f"圖片生成時發生錯誤: {str(e)}"
            }
    
    @staticmethod
    def get_available_models() -> Dict:
        """
        獲取可用的模型列表
        
        Returns:
            模型列表資訊
        """
        return {
            "success": True,
            "data": {
                "models": [
                    {
                        "id": "flux-schnell",
                        "name": "FLUX.1 Schnell",
                        "description": "速度快，品質優秀，推薦使用",
                        "recommended": True
                    },
                    {
                        "id": "sdxl",
                        "name": "Stable Diffusion XL",
                        "description": "高品質圖片生成",
                        "recommended": False
                    },
                    {
                        "id": "sd-1.5",
                        "name": "Stable Diffusion 1.5",
                        "description": "經典模型",
                        "recommended": False
                    }
                ],
                "default": ImageGenerationService.DEFAULT_MODEL
            },
            "message": "成功獲取模型列表"
        }
