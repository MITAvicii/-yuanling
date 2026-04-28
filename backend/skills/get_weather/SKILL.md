---
name: get_weather
description: 获取指定城市的实时天气信息
version: 1.0.0
author: system
---

# 获取天气技能

## 功能说明

获取指定城市的实时天气信息，包括温度、天气状况、湿度、风力等。

## 使用步骤

### 步骤 1：获取城市名称

确认用户要查询的城市名称。如果用户没有指定，询问用户要查询哪个城市。

### 步骤 2：调用天气 API

使用 `fetch_url` 工具访问以下 API：

```
https://wttr.in/{城市名}?format=j1
```

例如查询北京天气：
```
https://wttr.in/Beijing?format=j1
```

注意：城市名使用英文或拼音。

### 步骤 3：解析结果

API 返回 JSON 格式的天气数据，主要字段：

```json
{
  "current_condition": [{
    "temp_C": "25",
    "weatherDesc": [{"value": "Clear"}],
    "humidity": "45",
    "windspeedKmph": "12"
  }]
}
```

### 步骤 4：格式化输出

将天气信息以友好的格式展示给用户：

```
📍 城市：北京
🌡️ 温度：25°C
☁️ 天气：晴
💧 湿度：45%
💨 风速：12 km/h
```

## 示例对话

用户：查询北京的天气

助手：
1. 使用 `fetch_url` 获取 `https://wttr.in/Beijing?format=j1`
2. 解析 JSON 数据
3. 返回格式化的天气信息

## 注意事项

- 如果 API 调用失败，提示用户稍后重试
- 城市名建议使用英文或拼音
- 天气数据为实时数据，可能存在延迟
