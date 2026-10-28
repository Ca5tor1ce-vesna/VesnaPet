# VesnaPet（薇斯纳桌宠）

Windows 桌宠：原版可独立运行；新功能走可选 DLC（食物、特殊互动、语音、聊天）。

## 结构

- 根目录：原版桌宠（`run.bat` / `main.py`）
- `dlc/foods`：食物与整蛊包
- `dlc/interactions`：安抚、陪同奖励、旋转呕吐、强制浇水等
- `dlc/voice`：语音素材
- `dlc/chat`：独立 LLM 聊天窗口（需自备 OpenAI 兼容 API Key，勿把密钥提交进仓库）

## 运行

见 `README.txt`。聊天包见 `dlc/chat/run.bat`。

## 说明

本仓库来自助手电脑上的工作快照（约 2026-10-16 前后的原版 + DLC；聊天包含单实例限制等修复）。运行时状态与 API 密钥不入库。
