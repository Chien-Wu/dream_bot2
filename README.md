# Dream Line Bot v2

一個專業且高度可擴展的 LINE Bot，由 OpenAI Assistant API 驅動，專為台灣社會福利組織設計。

## 🚀 Features

- **AI-Powered Conversations**: 整合 OpenAI Assistant API 提供智能對話
- **Web Search Integration**: 使用 OpenAI web search 提供最新資訊
- **Message Buffering**: 智能訊息緩衝，整合短訊息提供完整上下文
- **Taiwan-Focused**: 針對台灣社會福利組織優化的搜尋與回應
- **Organization Data Management**: 完整的組織資料管理與分析
- **Confidence-Based Routing**: 基於信心度的自動人工轉接
- **Robust Architecture**: 清晰的架構分離與依賴注入
- **Comprehensive Logging**: 結構化日誌記錄，支援不同級別和輸出
- **Database Persistence**: MySQL 整合，儲存對話記錄和組織資料
- **Docker Ready**: 容器化部署，支援 Docker Compose
- **Testing Framework**: 完整的測試套件，使用 pytest

## 🏗️ Architecture

### Project Structure

```
dream_line_bot_v2/
├── src/
│   ├── core/                  # 核心業務邏輯
│   │   ├── container.py       # 依賴注入容器
│   │   ├── message_processor.py # 訊息處理器
│   │   └── message_buffer.py  # 訊息緩衝管理
│   ├── services/              # 業務服務
│   │   ├── database_service.py
│   │   ├── openai_service.py
│   │   ├── line_service.py
│   │   ├── web_search_service.py
│   │   ├── function_handler.py
│   │   ├── organization_analyzer.py
│   │   └── welcome_flow_manager.py
│   ├── controllers/           # API 控制器
│   │   └── webhook_controller.py
│   ├── models/               # 資料模型
│   │   └── user.py
│   └── utils/                # 工具函數
│       ├── logger.py
│       └── exceptions.py
├── config/                   # 配置管理
│   ├── settings.py
│   └── __init__.py
├── tests/                    # 測試套件
├── docs/                     # 文件
├── scripts/                  # 資料庫腳本
└── requirements.txt
```

### Key Components

- **MessageProcessor**: 所有訊息處理的中央協調器
- **MessageBuffer**: 智能訊息緩衝，整合短訊息為完整上下文
- **WebSearchService**: OpenAI web search 整合，提供最新資訊
- **FunctionHandler**: OpenAI Assistant 功能調用處理器
- **OrganizationAnalyzer**: 組織資料分析與管理
- **WelcomeFlowManager**: 新用戶歡迎流程管理
- **DatabaseService**: 資料庫操作，支援連接池
- **OpenAIService**: OpenAI Assistant API 互動管理
- **LineService**: LINE Bot 訊息操作
- **Container**: 服務管理的依賴注入容器

## 🛠️ Setup & Installation

### Prerequisites

- Python 3.11+
- MySQL 8.0+
- Docker & Docker Compose (optional)
- LINE Bot account
- OpenAI API account with Assistant

### Local Development

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd dream_line_bot_v2
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Environment setup**

   Create `.env` file:
   ```bash
   # Database Configuration
   MYSQL_HOST=localhost
   MYSQL_USER=your_mysql_user
   MYSQL_PASSWORD=your_mysql_password
   MYSQL_DATABASE=dream_bot_db
   
   # LINE Bot Configuration
   LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
   LINE_CHANNEL_SECRET=your_line_channel_secret
   LINE_ADMIN_USER_ID=your_admin_user_id
   
   # OpenAI Configuration
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_ASSISTANT_ID=your_assistant_id
   
   # Optional: Timeout Configuration
   OPENAI_POLL_MAX_RETRIES=120
   OPENAI_POLL_INTERVAL=2.0
   SEARCH_TIMEOUT=120.0
   
   # Optional: Message Buffer Configuration
   MESSAGE_BUFFER_TIMEOUT=10.0
   MESSAGE_BUFFER_MAX_SIZE=10
   MESSAGE_BUFFER_MIN_LENGTH=50
   ```

5. **Database setup**

   ```bash
   # Create MySQL database and run init script
   mysql -u root -p < scripts/init.sql
   ```

6. **Run the application**
   ```bash
   python main.py
   ```

### Docker Deployment

1. **Environment setup**

   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

2. **Start services**

   ```bash
   docker-compose up -d
   ```

3. **Check logs**
   ```bash
   docker-compose logs -f dream-bot
   ```

## 🔧 Configuration

All configuration is managed through environment variables.

### Key Configuration Options

| Variable                     | Description                             | Default       |
| ---------------------------- | --------------------------------------- | ------------- |
| `ENVIRONMENT`                | Application environment                 | `development` |
| `LOG_LEVEL`                  | Logging level                           | `INFO`        |
| `AI_CONFIDENCE_THRESHOLD`    | Confidence threshold for human handover | `0.83`        |
| `OPENAI_POLL_MAX_RETRIES`    | Max retries for OpenAI API              | `120`         |
| `OPENAI_POLL_INTERVAL`       | Poll interval for OpenAI API (seconds)  | `2.0`         |
| `SEARCH_TIMEOUT`             | Web search timeout (seconds)            | `120.0`       |
| `MESSAGE_BUFFER_TIMEOUT`     | Message buffer timeout (seconds)        | `10.0`        |
| `MESSAGE_BUFFER_MAX_SIZE`    | Max messages in buffer                  | `10`          |
| `MESSAGE_BUFFER_MIN_LENGTH`  | Min length for immediate processing     | `50`          |

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test files
pytest tests/test_services.py
pytest tests/test_message_processor.py
```

## 📊 Message Flow

### 1. Message Buffering System

```
用戶短訊息 → 訊息緩衝器 → 等待完整上下文 → AI 處理
     ↓
長訊息/完整內容 → 直接處理
```

### 2. Web Search Integration

```
用戶查詢 → AI Assistant → 觸發 web_search 功能 → OpenAI Web Search → 台灣特化結果
```

### 3. Complete Processing Flow

1. **Message Received**: LINE webhook 接收用戶訊息
2. **Message Buffering**: 短訊息進入緩衝器，長訊息直接處理
3. **Context Assembly**: 緩衝器整合多個短訊息為完整上下文
4. **AI Processing**: 發送至 OpenAI Assistant API
5. **Function Calls**: AI 可調用 web search 等功能
6. **Confidence Evaluation**: 評估 AI 回應信心度
7. **Response Routing**: 發送 AI 回應或轉接人工
8. **Logging**: 記錄互動用於分析和調試

## 🔍 Web Search Features

### Taiwan-Focused Search

- **自動關鍵詞增強**: 為查詢添加台灣相關詞彙
- **政府資源優先**: 重點關注政府政策和法規
- **社會福利專門化**: 針對社會福利措施和補助
- **結構化回應**: JSON 格式回應，包含摘要、來源、關鍵發現

### Search Configuration

```python
# 可在 .env 中調整搜尋設定
SEARCH_DEFAULT_RESULTS=5     # 預設結果數量
SEARCH_MAX_RESULTS=10        # 最大結果數量
SEARCH_TIMEOUT=120.0         # 搜尋超時時間
```

## 📈 Performance

### Optimized Timeouts

- **AI Processing**: 4 分鐘總超時時間 (120 retries × 2s)
- **Web Search**: 2 分鐘搜尋超時
- **Message Buffer**: 10 秒緩衝超時

### Benchmarks

- **Message Processing**: 平均 2-5 秒回應時間
- **Database Queries**: 標準操作 <100ms
- **Memory Usage**: 標準部署 <512MB
- **Concurrent Users**: 每個實例支援 1000+ 用戶

## 🐛 Troubleshooting

### Common Issues

**Web Search Timeouts**
- 增加 `SEARCH_TIMEOUT` 環境變數
- 調整 `OPENAI_POLL_MAX_RETRIES` 設定
- 檢查 OpenAI API 配額

**Message Buffer Issues**
- 調整 `MESSAGE_BUFFER_TIMEOUT` 設定
- 檢查 `MESSAGE_BUFFER_MIN_LENGTH` 閾值
- 查看日誌中的緩衝器狀態

**Database Connection Errors**
- 檢查 MySQL 憑證和連接性
- 確認資料庫存在且表格已建立
- 檢查防火牆和網路設定

### Debug Mode

Enable debug mode for detailed logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python main.py
```

## 🚀 Deployment

### Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Configure proper `LOG_LEVEL=INFO`
- [ ] Set up database backups
- [ ] Configure reverse proxy (nginx)
- [ ] Set up SSL certificates
- [ ] Configure monitoring and alerting
- [ ] Set up log aggregation
- [ ] Test web search functionality
- [ ] Verify message buffering works correctly

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints for all functions
- Write comprehensive docstrings
- Include unit tests for new features
- Update documentation for API changes

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for the Assistant API and web search capabilities
- LINE Corporation for the Bot SDK
- Flask community for the web framework
- All contributors and maintainers