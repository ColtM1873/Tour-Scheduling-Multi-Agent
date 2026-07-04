# 🧳 Tour-Scheduling-Multi-Agent

一个基于 **LangGraph DeepAgents** 的复杂旅游行程规划多智能体系统。

主 Agent 协调 **地图、天气、铁路票务、联网搜索** 四位子 Agent，自动完成从路线规划、天气查询、火车票检索到中转方案的全链路决策，并最终输出精美的 HTML 行程单。

**许可证**：[GPL-3.0](LICENSE)  
依赖的核心项目：

- 地图工具：[gaode_map_mcp](https://github.com/ColtM1873/Gaode-Map-MCP)
- 天气工具：
  - [彩云天气 MCP](https://github.com/caiyunapp/mcp-caiyun-weather)
  - 聚合天气 MCP
- 联网搜索工具：[mcp-searxng](https://github.com/ihor-sokoliuk/mcp-searxng)
- 铁路票务工具：[mcp-server-12306](https://github.com/drfccv/mcp-server-12306)

---

## 🧠 架构概览

```
用户输入
   ↓
主 Agent (DeepAgent)
   ├── Map Agent (地图规划，含骑行/公交/驾车)
   ├── Weather Agent (天气查询，彩云＋聚合)
   ├── Railway Agent (12306 票务 + 站内中转 + 餐食规划)
   └── Web Search Agent (SearXNG 联网搜索)
   ↓
汇总 → 输出 HTML 行程单
```

所有子 Agent 和主 Agent 均通过 MCP 协议调用外部工具，支持长短期记忆（PostgreSQL + SQLite），用户偏好会被持久化到 `/memories/AGENTS.md`。

---

## 🛠️ 依赖的外部服务

| 服务 | 用途 | 部署方式 | 获取地址 |
|---|---|---|---|
| **高德地图 API** | 地理编码、路线规划、POI 搜索 | 云 API，无需部署 | [高德开放平台](https://lbs.amap.com/) |
| **彩云天气 API** | 实时 / 逐小时 / 未来三天天气 | 云 API + 本地 MCP | [彩云天气](https://caiyunapp.com/) |
| **聚合天气 API** | 补充天气数据 | 云 MCP | [聚合数据](https://www.juhe.cn/) |
| **12306 MCP Server** | 火车票查询、中转规划 | 本地或远程 HTTP MCP | [mcp-server-12306](https://github.com/drfccv/mcp-server-12306) |
| **SearXNG MCP Server** | 联网搜索 | 本地或远程 HTTP MCP | [mcp-searxng](https://github.com/ihor-sokoliuk/mcp-searxng) |
| **PostgreSQL** | 存储用户记忆（偏好、历史） | 本地或云数据库 | 自备 |
| **LLM API** | 驱动所有 Agent 的推理 | 可自选（推荐至少 7B 以上模型） |

---

## 📦 安装与配置

### 1. 克隆仓库

```bash
git clone https://github.com/ColtM1873/Tour-Scheduling-Multi-Agent.git
cd Tour-Scheduling-Multi-Agent
```

### 2. 安装 Python 依赖

```bash
pip install langchain-mcp-adapters deepagents langchain langgraph psycopg2-binary python-dotenv
```

> 请确保 Python 版本 ≥ 3.10。

### 3. 获取并配置外部服务

#### 🔹 高德地图 API Key

1. 前往 [高德开放平台](https://lbs.amap.com/)，创建应用，获取 Web 服务的 Key。
2. 将 Key 填入 `.env` 中的 `GAODE_MAP_API_KEY=""`（替换两处的占位符）。

#### 🔹 彩云天气 API Token

1. 注册 [彩云天气](https://caiyunapp.com/)，获取 API Token。
2. 填入 `.env` 中的 `CAIYUN_WEATHER_API_TOKEN=""`。

#### 🔹 聚合天气 MCP Server

由于聚合天气官方未提供标准 MCP 封装，你需要：

- 在聚合数据官网申请天气相关 MCP API link URL；
- 将 URL 填入 `compact_agent.py` 中 `juhe_weather_search` 的 `url` 字段。

#### 🔹 12306 MCP Server

```bash
git clone https://github.com/drfccv/mcp-server-12306.git
cd mcp-server-12306
# 按该仓库说明启动 HTTP 服务
# 记录服务地址，如 http://localhost:8080
```

将 `compact_agent.py` 中 `railway_client` 的 `url` 替换为你的服务地址。

#### 🔹 SearXNG + MCP Server

1. 先启动一个 SearXNG 实例（Docker 最简便）：
   ```bash
   docker run -d --name searxng -p 8081:8080 searxng/searxng
   ```
2. 再启动 mcp-searxng：
   ```bash
   git clone https://github.com/ihor-sokoliuk/mcp-searxng.git
   # 参照项目文档配置并启动 HTTP 模式
   ```
3. 将 `compact_agent.py` 中 `web_search_client` 的 `url` 替换为对应地址。

#### 🔹 PostgreSQL (记忆存储)

建议使用 Docker 快速部署：

```bash
docker run --name mypostgres -e POSTGRES_PASSWORD=yourpassword -p 5432:5432 -d postgres
```

然后修改 `compact_agent.py` 中的连接字符串：

```python
conn_string = "postgresql://postgres:yourpassword@localhost:5432/postgres"
```

该数据库用于存储用户偏好 (`/memories/AGENTS.md`)，如无需记忆功能可删除相关代码，但会失去个性化能力。

#### 🔹 MCP 文件路径

在 `compact_agent.py` 中，请将以下路径改为您本机的实际路径：

```python
"args": ["You\\Path\\to\\gaode_map_mcp.py"],          # gaode_map_mcp.py 的绝对路径
"args": ["You\\Path\\To\\caiyun_weather_mcp.py"],    # caiyun_weather_mcp.py 的绝对路径
```

#### 🔹 LLM 配置

该工程支持 5 个独立的 LLM API Key，以便为不同 Agent 分配不同模型（节省成本或提升性能）。在 `.env` 中填写对应的 Key：

```ini
MAIN_AGENT_LLM_API_KEY = "sk-xxx"
RAILWAY_AGENT_LLM_API_KEY = "sk-xxx"
MAP_AGENT_LLM_API_KEY = "sk-xxx"
WEB_AGENT_LLM_API_KEY = "sk-xxx"
WEATHER_AGENT_LLM_API_KEY = "sk-xxx"
```

然后在 `compact_agent.py` 的 `init_chat_model` 中指定模型名称（如 `"gpt-4o"`、`"deepseek-chat"`、`"qwen-plus"` 等）。

---

## 🚀 运行

确认所有外部服务就绪后，直接执行：

```bash
python compact_agent.py
```

程序会提示你输入旅游需求，例如：

```
请输入你的旅游规划详细要求：我从上海出发去北京玩三天，预算3000元，喜欢博物馆。
```

等待片刻，程序会输出 `output_from_main_agent.html`，双击即可查看精美的行程单。

---

## 📝 子 Agent 职责说明

| Agent | 专属工具 | 职责 |
|---|---|---|
| **Map Agent** | `gaode_map_mcp` 全部工具 | 市内路径规划（骑行/公交/驾车）、周边 POI 搜索 |
| **Weather Agent** | `caiyun_weather_mcp` + `juhe_weather_mcp` + 2 个地图工具 | 实时天气、预报、预警，自动将地名转经纬度 |
| **Railway Agent** | `12306 MCP` + 地图的公共交通工具 | 火车票查询、同城不同站换乘接驳、餐食点推荐 |
| **Web Search Agent** | `SearXNG MCP` | 补充网络信息（如景点开放时间、民俗活动） |

主 Agent 负责分析用户意图、拆解任务、调度子 Agent，并综合所有信息生成最终 HTML。

---

## 🧪 调试建议

- 运行后查看控制台最后输出的 `reasoning_content`（需模型支持），可见主 Agent 的思考过程。
- 如需检查单步工具调用，可临时在 `create_deep_agent` 中添加 `verbose=True`。
- 首次运行时，请确认所有 MCP 服务器均已启动且路径/URL 正确。

---

## ❓ 常见问题

**Q：为什么需要 PostgreSQL？我只想临时用一下。**  
A：可以移除 `create_deep_agent` 中的 `memory` 和 `backend` 参数，这样记忆功能会丢失，但不影响基本规划。

**Q：没有聚合天气怎么办？**  
A：可暂时在 `weather_agent` 的 `tools` 里移除 `juhe_weather_search`，只保留彩云天气即可。

**Q：如何支持中转规划？**  
A：在输入中明确说明“需要考虑中转”，主 Agent 会将该指令传给 Railway Agent，后者会利用地图工具规划换乘方案。

---

## 🙏 致谢

- [gaode_map_mcp](https://github.com/ColtM1873/Gaode-Map-MCP) - 高德地图 MCP 封装
- [mcp-caiyun-weather](https://github.com/caiyunapp/mcp-caiyun-weather) - 彩云天气 MCP
- [mcp-searxng](https://github.com/ihor-sokoliuk/mcp-searxng) - SearXNG MCP 封装
- [mcp-server-12306](https://github.com/drfccv/mcp-server-12306) - 12306 MCP 服务
- [DeepAgents](https://github.com/langchain-ai/deepagents) - 多智能体框架
- [LangChain](https://github.com/langchain-ai/langchain) - 大模型应用框架

---

## ⭐ 支持一下

如果你觉得这个项目有用，请给一个 **Star** ⭐，这是对开源最大的鼓励！  
也欢迎提交 Issue 或 PR 一起完善。

[![Star History Chart](https://api.star-history.com/svg?repos=ColtM1873/Tour-Scheduling-Multi-Agent&type=Date)](https://star-history.com/#ColtM1873/Tour-Scheduling-Multi-Agent&Date)

---

## 📄 License

GPL-3.0 © ColtM1873

