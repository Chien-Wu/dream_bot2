#!/usr/bin/env python3
"""
Test script for the /analyze command AI functionality.
"""

import sys
sys.path.append('.')

from unittest.mock import Mock, patch
from src.services.admin_command_service import AdminCommandService
from src.models import AIResponse


def test_analyze_command():
    """Test the analyze command functionality."""
    print("🧪 Testing /analyze Command AI Integration")
    print("=" * 50)
    
    # Create mock services
    mock_db = Mock()
    mock_line = Mock()
    
    # Mock failed questions data
    mock_failed_questions = [
        {
            'content': '如何申請社會福利補助？',
            'confidence': 0.45,
            'frequency': 3,
            'ai_response': '需要準備相關文件...',
            'created_at': '2024-01-15'
        },
        {
            'content': '身心障礙證明要怎麼辦理？',
            'confidence': 0.52,
            'frequency': 2,
            'ai_response': '請聯絡相關單位...',
            'created_at': '2024-01-14'
        }
    ]
    
    # Mock database query to return failed questions
    mock_db.execute_query.return_value = [
        mock_failed_questions[0],
        mock_failed_questions[1]
    ]
    
    # Create admin service
    admin_service = AdminCommandService(mock_db, mock_line)
    
    # Test 1: Check if completion API method exists
    print("\n--- Test 1: Completion API Method ---")
    try:
        if hasattr(admin_service, '_call_openai_completion'):
            print("✅ Completion API method exists")
        else:
            print("❌ Completion API method missing")
    except Exception as e:
        print(f"❌ Method check error: {e}")
    
    # Test 2: Test with mock completion API
    print("\n--- Test 2: Mock Completion API ---")
    try:
        # Mock the completion API call
        expected_result = """**主要問題類型：** 社會福利申請、身心障礙服務、政府補助

**最重要問題範例：**
1. 如何申請社會福利補助？
2. 身心障礙證明要怎麼辦理？
3. 長期照護服務申請流程
4. 兒童發展遲緩早期療育
5. 弱勢家庭急難救助"""
        
        # Patch the completion API method
        with patch.object(admin_service, '_call_openai_completion', return_value=expected_result):
            # Test the analysis method directly
            result = admin_service._analyze_questions_with_ai(mock_failed_questions, 7)
            
            print(f"✅ AI Analysis Result:")
            print(f"   Length: {len(result)} characters")
            print(f"   Contains '主要問題類型': {'主要問題類型' in result}")
            print(f"   Contains '最重要問題範例': {'最重要問題範例' in result}")
            print(f"   First 100 chars: {result[:100]}...")
        
    except Exception as e:
        print(f"❌ Mock completion API error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Test full command execution
    print("\n--- Test 3: Full Command Execution ---")
    try:
        # Execute the analyze command
        result = admin_service.execute_command("analyze", ["7", "50"])
        
        print(f"Command execution result:")
        print(f"   Success: {result.success}")
        print(f"   Message length: {len(result.message)} characters")
        print(f"   Has data: {result.data is not None}")
        print(f"   First 200 chars: {result.message[:200]}...")
        
        if not result.success:
            print(f"   Error: {result.error}")
        
    except Exception as e:
        print(f"❌ Full command execution error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ Testing completed!")


def test_simplified_analyze():
    """Test a simplified version to isolate issues."""
    print("\n🔧 Testing Simplified Analysis Logic")
    print("=" * 50)
    
    # Test the core logic without dependencies
    questions = [
        {'content': '測試問題1', 'confidence': 0.4, 'frequency': 2},
        {'content': '測試問題2', 'confidence': 0.5, 'frequency': 1}
    ]
    
    # Test prompt generation
    questions_text = ""
    for i, q in enumerate(questions, 1):
        content = q.get('content', '')[:200]
        confidence = q.get('confidence', 0)
        frequency = q.get('frequency', 1)
        questions_text += f"{i}. [{confidence:.2f}] [出現{frequency}次] {content}\n"
    
    analysis_prompt = f"""分析以下 {len(questions)} 個低信心度問題（過去7天內），請提供簡潔分析：

問題列表：
{questions_text}

請按以下格式回答：

**主要問題類型：** [類型1]、[類型2]、[類型3]

**最重要問題範例：**
1. [最重要的問題1]
2. [最重要的問題2] 
3. [最重要的問題3]
4. [最重要的問題4]
5. [最重要的問題5]

請用繁體中文，保持簡潔。"""
    
    print(f"✅ Generated prompt:")
    print(f"   Length: {len(analysis_prompt)} characters")
    print(f"   Contains questions: {len(questions)} questions included")
    print(f"   Sample: {analysis_prompt[:300]}...")


if __name__ == "__main__":
    try:
        test_analyze_command()
        test_simplified_analyze()
    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted")
    except Exception as e:
        print(f"\n💥 Testing failed: {e}")
        import traceback
        traceback.print_exc()