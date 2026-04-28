## 已知用户

以下是已经与机器人交互过的用户，可以在其他对话中直接使用这些open_id：

### 当前用户（需要发送AI新闻的用户）
- **状态**: 已发送"你好"消息，等待获取open_id
- **最后交互时间**: 2026-02-13
- **交互内容**: 发送了"你好"消息，请求发送AI科技新闻
- **备注**: 需要从飞书消息事件中获取实际的open_id

### 如何获取用户open_id
1. 用户在飞书中向机器人发送消息
2. 消息处理器会记录sender_open_id
3. 将open_id添加到known_users字典中
4. 在其他对话中直接使用

### 使用示例
```python
# 已知用户字典
known_users = {
    "ai_news_user": "需要从消息中获取的实际open_id",
    "test_user": "ou_xxxxxxxxxxxxxxxx"
}

# 发送消息给用户
async def send_to_user(user_key, content):
    from backend.platforms.feishu import get_feishu_connection
    import asyncio
    
    conn = get_feishu_connection()
    api_client = conn.api_client
    
    result = await api_client.send_message(
        receive_id=known_users[user_key],
        receive_id_type="open_id",
        content=content,
        msg_type="text"
    )
    return result

# 发送AI新闻给当前用户
ai_news = "🔥 AI科技新闻内容..."
asyncio.run(send_to_user("ai_news_user", ai_news))
```

