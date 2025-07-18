"""
Simple web search service using OpenAI's built-in web search capabilities.
"""
from typing import Dict, Any
import json
import re
import os
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

from config import config
from src.utils import setup_logger


logger = setup_logger(__name__)


class WebSearchService:
    """
    Simple web search service using OpenAI's web_search_preview tool.
    Much simpler and more reliable than complex provider architecture.
    """
    
    def __init__(self, openai_client: OpenAI = None):
        self.config = config.search
        self.openai_config = config.openai
        
        # Use provided client or create new one
        if openai_client:
            self.client = openai_client
        else:
            # Temporary fix: Load OpenAI API key directly from environment
            load_dotenv()
            api_key = os.getenv('OPENAI_API_KEY', self.openai_config.api_key)
            self.client = OpenAI(api_key=api_key)
        
        logger.info("WebSearchService initialized with OpenAI web search")
    
    def search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Perform web search using OpenAI's built-in web search.
        
        Args:
            query: Search query string
            num_results: Number of results to return
            
        Returns:
            Dictionary containing search results and analysis
        """
        try:
            logger.info(f"Starting OpenAI web search for: {query}")
            print(f"[DEBUG] Original query: {query}")
            
            # Enhance query for Taiwan social welfare context
            enhanced_query = self._enhance_query_for_taiwan(query)
            print(f"[DEBUG] Enhanced query: {enhanced_query}")
            
            # Create Taiwan-specific search prompt
            search_prompt = f"""
請搜尋與「{enhanced_query}」相關的最新台灣資訊，特別關注：
1. 台灣政府官方政策和法規
2. 社會福利相關措施和補助
3. 非營利組織相關資訊
4. 最新的政策變化和更新

請提供 {num_results} 個最相關的結果，並以以下JSON格式回應：
{{
    "summary": "搜尋結果的整體摘要和重要發現",
    "sources": [
        {{
            "title": "結果標題",
            "snippet": "內容摘要",
            "url": "網址",
            "source": "來源網站",
            "date": "發布日期（如果有）"
        }}
    ],
    "key_findings": [
        "重要發現1",
        "重要發現2",
        "重要發現3"
    ],
    "recommendations": "對台灣社福組織的具體建議"
}}

請確保資訊準確、最新，並與台灣的社會福利組織相關。
"""
            print(f"[DEBUG] Search prompt: {search_prompt}")
            
            # Use OpenAI responses API with web search
            print(f"[DEBUG] Calling OpenAI responses API...")
            response = self.client.responses.create(
                model="gpt-4o",
                tools=[{"type": "web_search_preview"}],
                input=search_prompt
            )
            
            print(f"[DEBUG] OpenAI response object: {response}")
            response_content = response.output_text
            print(f"[DEBUG] Response content: {response_content}")
            logger.info(f"OpenAI web search completed")
            
            # Parse the response
            result = self._parse_search_response(response_content, query, num_results)
            print(f"[DEBUG] Parsed result: {result}")
            
            logger.info(f"Web search completed with {result.get('total_results', 0)} results")
            return result
            
        except Exception as e:
            logger.error(f"OpenAI web search failed: {e}")
            return {
                "error": f"搜尋失敗: {str(e)}",
                "query": query,
                "sources": [],
                "total_results": 0,
                "summary": "網路搜尋服務發生錯誤",
                "key_findings": ["系統錯誤", "請稍後再試"],
                "recommendations": "請聯繫技術支援或稍後再試",
                "provider": "openai_web_search",
                "search_time": datetime.now().isoformat()
            }
    
    def _enhance_query_for_taiwan(self, query: str) -> str:
        """Enhance search query for Taiwan social welfare context."""
        # Add Taiwan-specific terms if not already present
        taiwan_terms = ['台灣', '政府', '社會福利', '補助', '法規']
        
        # Check if query already contains Taiwan-specific terms
        has_taiwan_context = any(term in query for term in taiwan_terms)
        
        if not has_taiwan_context:
            # Add Taiwan context to improve search results
            enhanced = f"{query} 台灣"
            
            # Add specific context for social welfare queries
            if any(keyword in query for keyword in ['政策', '補助', '福利', '法規', '申請']):
                enhanced += " 政府 社會福利"
        else:
            enhanced = query
        
        return enhanced
    
    def _parse_search_response(self, response_content: str, original_query: str, num_results: int) -> Dict[str, Any]:
        """Parse OpenAI web search response."""
        try:
            print(f"[DEBUG] Parsing response content...")
            # Try to extract JSON from response
            json_match = self._extract_json_from_response(response_content)
            print(f"[DEBUG] JSON match: {json_match}")
            
            if json_match:
                parsed = json.loads(json_match)
                print(f"[DEBUG] Parsed JSON: {parsed}")
                
                # Format the result
                result = {
                    "query": original_query,
                    "summary": parsed.get("summary", ""),
                    "sources": parsed.get("sources", []),
                    "total_results": len(parsed.get("sources", [])),
                    "key_findings": parsed.get("key_findings", []),
                    "recommendations": parsed.get("recommendations", ""),
                    "provider": "openai_web_search",
                    "search_time": datetime.now().isoformat()
                }
                
                # Validate and clean sources
                result["sources"] = self._validate_sources(result["sources"])
                result["total_results"] = len(result["sources"])
                
                return result
            else:
                # If no JSON found, create structured response from raw text
                return {
                    "query": original_query,
                    "summary": response_content,
                    "sources": [],
                    "total_results": 0,
                    "key_findings": ["網路搜尋已完成，請查看摘要內容"],
                    "recommendations": "請參考上述搜尋結果",
                    "raw_response": response_content,
                    "provider": "openai_web_search",
                    "search_time": datetime.now().isoformat()
                }
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            return {
                "query": original_query,
                "summary": response_content,
                "sources": [],
                "total_results": 0,
                "key_findings": ["網路搜尋已完成，請查看摘要內容"],
                "recommendations": "請參考上述搜尋結果",
                "raw_response": response_content,
                "provider": "openai_web_search",
                "search_time": datetime.now().isoformat()
            }
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from OpenAI response."""
        # Try to find JSON in markdown code blocks
        json_pattern = r'```json\n(.*?)\n```'
        match = re.search(json_pattern, response, re.DOTALL)
        if match:
            return match.group(1)
        
        # Try to find JSON without markdown
        json_pattern = r'\{.*\}'
        match = re.search(json_pattern, response, re.DOTALL)
        if match:
            return match.group(0)
        
        return None
    
    def _validate_sources(self, sources) -> list:
        """Validate and clean source data."""
        validated = []
        
        if not isinstance(sources, list):
            return validated
        
        for source in sources:
            if isinstance(source, dict):
                validated_source = {
                    "title": str(source.get("title", "")).strip(),
                    "snippet": str(source.get("snippet", "")).strip(),
                    "url": str(source.get("url", "")).strip(),
                    "source": str(source.get("source", "")).strip(),
                    "date": str(source.get("date", "")).strip() if source.get("date") else None
                }
                
                # Only add if it has at least title
                if validated_source["title"]:
                    validated.append(validated_source)
        
        return validated
    
    def get_search_analytics(self) -> Dict[str, Any]:
        """Get basic analytics (simplified for new architecture)."""
        return {
            "provider": "openai_web_search",
            "status": "active",
            "features": ["real_time_web_search", "taiwan_context", "social_welfare_focus"]
        }