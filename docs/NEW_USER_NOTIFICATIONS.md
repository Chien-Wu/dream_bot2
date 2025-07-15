# New User Notification System

The Dream Line Bot automatically notifies administrators when new users join the bot.

## 🔔 How It Works

### Automatic Detection
When a user adds or follows your LINE Bot, LINE sends a `FollowEvent` webhook to your bot. The system automatically:

1. **Detects the new user** via FollowEvent
2. **Notifies the admin** with user details
3. **Sends welcome message** to the new user
4. **Logs the event** for monitoring

### Current Flow
```
New User → Follows Bot → LINE FollowEvent → Bot Processes → Admin Notified + User Welcomed
```

## 📱 What the Admin Receives

When a new user joins, the admin gets a notification like:

```
用戶需要人工協助

用戶ID: U12345678901234567890123456789012
用戶訊息: 新用戶加入 LINE Bot
```

## 👋 What the New User Receives

The new user immediately gets a welcome message:

```
歡迎使用 Dream Bot！有什麼可以幫助您的嗎？
```

## ⚙️ Configuration

### Required Setting
Make sure your `.env` file has the admin user ID configured:

```bash
LINE_ADMIN_USER_ID=your_line_admin_user_id
```

### How to Get Your LINE User ID
1. Add your own bot as a friend
2. Send a message to your bot
3. Check the logs for your user ID
4. Add that ID to your `.env` file

## 🔧 Customization Options

### 1. Customize Welcome Message

Edit the welcome message in `src/controllers/webhook_controller.py`:

```python
# Current welcome message
welcome_message = "歡迎使用 Dream Bot！有什麼可以幫助您的嗎？"

# Customize it to your needs
welcome_message = "您好！歡迎使用我們的智能客服系統。我可以幫助您解答問題。"
```

### 2. Add More User Information

You can enhance the admin notification to include more details:

```python
# Enhanced notification
self.line.notify_admin(
    user_id=user_id,
    user_msg=f"新用戶加入 LINE Bot\n加入時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)
```

### 3. Disable Welcome Message

To disable the automatic welcome message, comment out these lines:

```python
# Optional: Send welcome message
# welcome_message = "歡迎使用 Dream Bot！有什麼可以幫助您的嗎？"
# self.line.push_message(user_id, welcome_message)
```

### 4. Add User Tracking

You can add database tracking for new users:

```python
# In the follow event handler
try:
    # Existing notification code...
    
    # Add user tracking
    self.db.log_new_user(user_id, datetime.now())
    
except Exception as e:
    logger.error(f"Error handling follow event: {e}")
```

## 📊 Monitoring

### Check Admin Notifications
The system logs all admin notifications:

```
INFO - Notified admin about user U12345678901234567890123456789012
```

### Monitor New User Events
User follow events are tracked:

```
INFO - [User:U12345678901234567890123456789012] User action: user_followed
```

### Health Check
You can verify the system is working by checking recent logs for new user events.

## 🚨 Troubleshooting

### Admin Not Receiving Notifications

1. **Check Configuration**
   ```bash
   # Verify admin user ID is set
   echo $LINE_ADMIN_USER_ID
   ```

2. **Test Notification Manually**
   ```bash
   python3 test_new_user_notification.py
   ```

3. **Check Logs**
   ```bash
   # Look for notification attempts
   grep "Notified admin" logs/dream_bot.log
   ```

### Welcome Message Not Sent

1. **Check LINE Bot Permissions**
   - Ensure bot can send push messages
   - Verify LINE channel settings

2. **Review Error Logs**
   ```bash
   grep "Error handling follow" logs/dream_bot.log
   ```

### Missing Follow Events

1. **Verify Webhook Setup**
   - Check LINE Developers Console webhook settings
   - Ensure webhook URL is correct and accessible

2. **Test Webhook**
   - Use LINE Bot simulator to test follow events

## 🔒 Security Considerations

### User Privacy
- Only the user ID is logged, no personal information
- User IDs are hashed in logs if privacy is a concern

### Admin Notifications
- Limit admin notifications to prevent spam
- Consider rate limiting for high-volume bots

## 📈 Analytics

You can enhance the system to track:

- **New user count per day/week/month**
- **User retention rates**
- **Popular welcome message responses**
- **Geographic distribution** (if available)

## 🛠️ Advanced Features

### Multiple Admins
Support multiple administrators:

```python
# In .env
LINE_ADMIN_USER_IDS=admin1_id,admin2_id,admin3_id

# In code
admin_ids = config.line.admin_user_ids.split(',')
for admin_id in admin_ids:
    self.line.notify_admin(user_id=user_id, user_msg="新用戶加入 LINE Bot")
```

### Rich Welcome Messages
Send rich content with buttons or carousel:

```python
# Rich welcome message with quick replies
from linebot.v3.messaging import QuickReply, QuickReplyItem, MessageAction

quick_reply = QuickReply(items=[
    QuickReplyItem(action=MessageAction(label="產品諮詢", text="我想了解產品")),
    QuickReplyItem(action=MessageAction(label="價格查詢", text="請問價格")),
    QuickReplyItem(action=MessageAction(label="聯繫客服", text="轉人工"))
])
```

### User Segmentation
Tag new users for targeted messaging:

```python
# Tag new users
user_tags = {
    'new_user': True,
    'join_date': datetime.now().isoformat(),
    'source': 'organic'  # or 'marketing', 'referral', etc.
}
```

---

The new user notification system provides immediate visibility into bot growth and ensures no new users go unnoticed! 🎉