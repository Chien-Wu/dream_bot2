"""
Organization Data Analyzer for extracting organization information from user messages.
"""
import openai
import json
from typing import Dict, List, Optional
from dataclasses import dataclass

from config import config
from src.utils import setup_logger


logger = setup_logger(__name__)


@dataclass
class OrganizationData:
    """Organization data structure."""
    organization_name: Optional[str] = None
    service_city: Optional[str] = None
    contact_info: Optional[str] = None
    service_target: Optional[str] = None


class OrganizationDataAnalyzer:
    """Analyzes user messages to extract organization information."""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=config.openai.api_key)
    
    def analyze_message(self, message: str, current_data: OrganizationData) -> Dict:
        """
        Analyze user message and extract organization data.
        
        Args:
            message: User's message
            current_data: Previously extracted data
            
        Returns:
            Dict with extracted_data, missing_fields, and completion_status
        """
        try:
            system_prompt = self._build_system_prompt(current_data)
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Update current data with extracted info
            updated_data = self._merge_data(current_data, result.get('extracted_data', {}))
            
            # Check completion status
            missing_fields = self._get_missing_fields(updated_data)
            completion_status = 'complete' if not missing_fields else ('partial' if any([
                updated_data.organization_name,
                updated_data.service_city,
                updated_data.contact_info,
                updated_data.service_target
            ]) else 'pending')
            
            return {
                'extracted_data': updated_data,
                'missing_fields': missing_fields,
                'completion_status': completion_status,
                'hint_message': self._generate_hint(missing_fields)
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ChatGPT response: {e}")
            return self._fallback_analysis(message, current_data)
        except Exception as e:
            logger.error(f"Error analyzing message: {e}")
            return self._fallback_analysis(message, current_data)
    
    def _build_system_prompt(self, current_data: OrganizationData) -> str:
        """Build system prompt for ChatGPT."""
        return f"""
你是一個專門分析社福組織資料的助手。請從用戶訊息中提取以下資訊：

1. 單位全名 (organization_name)
2. 服務縣市 (service_city) 
3. 聯絡人職稱+姓名+電話 (contact_info)
4. 服務對象 (service_target): 限定為 弱勢兒少、中年困境、孤獨長者、無助動物

目前已有資料：
- 單位全名: {current_data.organization_name or "未提供"}
- 服務縣市: {current_data.service_city or "未提供"}
- 聯絡人資訊: {current_data.contact_info or "未提供"}
- 服務對象: {current_data.service_target or "未提供"}

請以JSON格式回覆，包含：
{{
  "extracted_data": {{
    "organization_name": "提取到的單位全名或null",
    "service_city": "提取到的服務縣市或null",
    "contact_info": "提取到的聯絡人資訊或null",
    "service_target": "提取到的服務對象或null"
  }},
  "confidence": 0.0-1.0
}}

注意：
- 只提取明確提到的資訊，不要推測
- 服務對象必須是四個選項之一
- 如果沒有找到新資訊，對應欄位返回null
- 聯絡人資訊要包含職稱、姓名、電話
"""
    
    def _merge_data(self, current: OrganizationData, extracted: Dict) -> OrganizationData:
        """Merge current data with newly extracted data."""
        return OrganizationData(
            organization_name=extracted.get('organization_name') or current.organization_name,
            service_city=extracted.get('service_city') or current.service_city,
            contact_info=extracted.get('contact_info') or current.contact_info,
            service_target=extracted.get('service_target') or current.service_target
        )
    
    def _get_missing_fields(self, data: OrganizationData) -> List[str]:
        """Get list of missing required fields."""
        missing = []
        
        if not data.organization_name:
            missing.append("單位全名")
        if not data.service_city:
            missing.append("服務縣市")
        if not data.contact_info:
            missing.append("聯絡人職稱+姓名+電話")
        if not data.service_target:
            missing.append("服務對象")
            
        return missing
    
    def _generate_hint(self, missing_fields: List[str]) -> str:
        """Generate hint message for missing fields."""
        if not missing_fields:
            return "已收到資料並完成建檔！很高興認識貴單位，一起夢想會持續支持微型社福，期待未來有更多交流 🤜🏻🤛🏻"
        
        hint = "感謝您的加入，請先提供以下資訊：\n"
        count = 0
        if "單位全名" in missing_fields:
            hint += "1、單位全名：\n"
            count += 1
        if "服務縣市" in missing_fields:
            hint += "2、服務縣市：\n"
            count += 1
        if "聯絡人職稱+姓名+電話" in missing_fields:
            hint += "3、聯絡人職稱+姓名+電話：\n"
            count += 1
        if "服務對象" in missing_fields:
            hint += "4、服務對象（可複選）：弱勢兒少、中年困境、孤獨長者、無助動物。\n"
            count += 1

        if count == 4:
            hint += "📌 一起夢想已啟用 AI 客服，能即時回答常見問題，幫助您更快得到回覆，若 AI 無法解決，也能隨時請專人接手，請放心使用！"
        
        return hint
    
    def _fallback_analysis(self, message: str, current_data: OrganizationData) -> Dict:
        """Fallback analysis using keyword matching."""
        logger.info("Using fallback keyword analysis")
        
        # Simple keyword matching as fallback
        extracted = {}
        
        # Check for organization name patterns
        if any(keyword in message for keyword in ['單位', '組織', '協會', '基金會', '社福']):
            # Extract potential organization name
            pass
        
        # Check for city names
        taiwan_cities = ['台北', '新北', '桃園', '台中', '台南', '高雄', '基隆', '新竹', '嘉義', '宜蘭', '苗栗', '彰化', '南投', '雲林', '屏東', '台東', '花蓮', '澎湖', '金門', '連江']
        for city in taiwan_cities:
            if city in message:
                extracted['service_city'] = city
                break
        
        # Check for service targets
        service_targets = ['弱勢兒少', '中年困境', '孤獨長者', '無助動物']
        for target in service_targets:
            if target in message:
                extracted['service_target'] = target
                break
        
        updated_data = self._merge_data(current_data, extracted)
        missing_fields = self._get_missing_fields(updated_data)
        completion_status = 'complete' if not missing_fields else ('partial' if any([
            updated_data.organization_name,
            updated_data.service_city,
            updated_data.contact_info,
            updated_data.service_target
        ]) else 'pending')
        
        return {
            'extracted_data': updated_data,
            'missing_fields': missing_fields,
            'completion_status': completion_status,
            'hint_message': self._generate_hint(missing_fields)
        }