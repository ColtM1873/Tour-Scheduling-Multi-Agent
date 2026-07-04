import asyncio
import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv
from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langgraph.store.postgres import AsyncPostgresStore
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from deepagents.backends.utils import create_file_data
from deepagents.backends import CompositeBackend,StateBackend, StoreBackend

load_dotenv()
MAIN_AGENT_LLM_API_KEY = os.getenv("MAIN_AGENT_LLM_API_KEY")
RAILWAY_AGENT_LLM_API_KEY = os.getenv("RAILWAY_AGENT_LLM_API_KEY")
MAP_AGENT_LLM_API_KEY = os.getenv("MAP_AGENT_LLM_API_KEY")
WEB_AGENT_LLM_API_KEY = os.getenv("WEB_AGENT_LLM_API_KEY")
WEATHER_AGENT_LLM_API_KEY = os.getenv("WEATHER_AGENT_LLM_API_KEY")


######################################### map_tools #########################################
map_client = MultiServerMCPClient(
    {
        "map_consult": {
            "command": "python",
            "args": ["You\\Path\\to\\gaode_map_mcp.py"],
            "transport" : "stdio"
        },
    }
)
async def return_map_tools():
    tools = await map_client.get_tools()
    return tools
map_tools = asyncio.run (
    return_map_tools()
 ) #return type of list, list[Structured Tools]


######################################### railway_tools #########################################
railway_client = MultiServerMCPClient(
    {
        "12306": {
            "transport": "http",
            "url": "link to your 12306 mcp server",
        },
    }
)
async def return_railway_tools():
    tools = await railway_client.get_tools()
    return tools
railway_tools = asyncio.run (
    return_railway_tools()
 )


######################################### web_search_tools #########################################
web_search_client = MultiServerMCPClient(
    {
        "web_search": {
            "transport": "http",
            "url": "link to your searXNG MCP server",
        },
    }
)
async def return_web_search_tools():
    tools = await web_search_client.get_tools()
    return tools
web_search_tools = asyncio.run (
    return_web_search_tools()
 )


######################################### weather_tools #########################################
weather_client = MultiServerMCPClient(
    {
        "caiyun_weather_search": {
            "command": "python",
            "args": ["You\\Path\\To\\caiyun_weather_mcp.py"],
            "transport" : "stdio"
        },
        "juhe_weather_search" :{
            "transport":"http",
            "url":"MCP server link here for your juhe_weather_search"
        }

    }
)
async def return_weather_tools():
    tools = await weather_client.get_tools()
    return tools
weather_tools = asyncio.run (
    return_weather_tools()
 )


######################################### railway_agent #########################################
railway_agent_description = """
铁路票务相关信息查询子agent。
遇到跨城市行程，或者你觉得有必要用到铁路交通的，交由他来获得铁路的票务信息
（起点站，终点站，发车时间，到达时间，车票价格等）
给定出发地和目的地后，默认只搜索直达车次。如果用户说需要考虑中转，需要明确地告诉railway_agent，你需要考虑中转，
或者更明确地，直接跟他说考虑从某个城市，或者某个火车站进行中转。
用户拿不准中转选择，你也拿不准的，可以问另一个子agent，web_search_agent，他负责联网搜索。
railway_agent会自动给出 在同城市换乘，但是火车站不同的情况下，乘坐地铁或者网约车到另一个火车站的路线规划。
你还可以显式地要求他提供中转时需要解决午饭或者其他餐食需求，他会为你做进一步规划。
"""

railway_agent_system_prompt = """
你是一个铁路票务，以及换乘，以及可能的换乘餐食规划助手。
你主要是作为子agent为主agent提供上述的信息，返回信息时，把部分票务原始信息返回，不要过于笼统，主agent可能会根据更多的信息集成来做决策。
你拥有一部分铁路相关的工具，一部分地图相关的工具，应该主要依赖铁路工具，如query-ticket-price。
地图工具中的public_transit_route_planning在起点和终点不同城时也会包含铁路路线规划，但是应该只在别无他法时依赖这部分信息。
你的大部分任务是调用地图工具，根据主agent提供的中转信息和站点建议，给出铁路票务和车次信息。
只有在中转方案同城不同站时，你才应该调用地图工具。
"""

railway_agent = {
    "name" : "railway_agent",
    "description" : railway_agent_description,
    "system_prompt" : railway_agent_system_prompt,
    "tools" : railway_tools + map_tools,
    "model" : init_chat_model(
        model = "you_llm_providers_model_name",
        api_key = RAILWAY_AGENT_LLM_API_KEY,
    )
}


######################################### web_search_agent #########################################
web_search_agent_description = """
联网搜索子agent。
将你需要联网搜索的内容，需要注意的事项，详尽地告诉他即可。
"""

web_search_agent_system_prompt = """
你是一个联网搜索助手。
你主要是作为子agent为主agent提供联网搜索的信息。
返回信息时，视主agent的要求，以及你自己的判断，返回归纳概括过的内容，或者是原始，详尽的网页内容。
"""

web_search_agent = {
    "name" : "web_search_agent",
    "description" : web_search_agent_description,
    "system_prompt" : web_search_agent_system_prompt,
    "tools" : web_search_tools,
    "model" : init_chat_model(
        model = "you_llm_providers_model_name",
        api_key = WEB_AGENT_LLM_API_KEY,
    )
}

######################################### weather_agent #########################################
weather_agent_description = """
天气查询子agent。
能够查询实时天气，逐小时天气，未来三天天气以及天气预警。
可以视情况自主判断，查询出发地，或者目的地，或者中途中转地的，哪一天的天气。
把你的要求详细地跟他说就行。
(最远只能查询未来三天的天气预报)
"""

weather_agent_system_prompt = """
你是一个天气查询助手。
你主要是作为子agent为主agent提供天气查询的信息。
返回信息时，视主agent的要求，以及你自己的判断，返回归纳概括过的内容，或者是原始的天气数据。
对于需要经纬度的天气工具，调用geocoding工具，如果geocoding没找到，再调用keyword_search_of_poi工具。
"""

selected_tools = {"geocoding" , "keyword_search_of_poi"}
map_tools_for_weather_agent = [x for x in map_tools if (x.name in selected_tools)]

weather_agent = {
    "name" : "weather_agent",
    "description" : weather_agent_description,
    "system_prompt" : weather_agent_system_prompt,
    "tools" : weather_tools + map_tools_for_weather_agent,
    "model" : init_chat_model(
        model = "you_llm_providers_model_name",
        api_key = WEATHER_AGENT_LLM_API_KEY,
    )
}

######################################### map_agent #########################################
map_agent_description = """
地图信息查询子agent。
不跨城情况下，行程规划任务的不二选择。
可以查询骑行，公共交通，驾车（网约车）等多种行程实现方式，还可以查询购物，美食以及风景名胜地点，
把你的要求（用户的要求），比如赶时间，压成本等等，详尽地告诉他吧！

对于跨城市行程规划，则应该主要考虑：
用户所在地到出发地火车站，以及目的地火车站到用户最终目的地
这两段路程，应该交给map_agent来完成哦。
"""

map_agent_system_prompt = """
你是一个地图查询（地图行程规划）助手。
你主要是作为子agent为主agent提供地图查询（地图行程规划）的能力。
返回信息时，把部分原始信息返回，不要过于笼统，主agent可能会根据他那边更多的信息集成来做决策，如果返回过于笼统或者概括的信息，主agent就难以做出更好的集成决策。
"""

map_agent = {
    "name" : "map_agent",
    "description" : map_agent_description,
    "system_prompt" : map_agent_system_prompt,
    "tools" : map_tools,
    "model" : init_chat_model(
        model = "you_llm_providers_model_name",
        api_key = MAP_AGENT_LLM_API_KEY,
    )
}


######################################### main_agent #########################################
subagents = [map_agent , weather_agent , railway_agent , web_search_agent]


main_agent_system_prompt = """
你是一个为用户规划行程的agent，你手下有4位子agent供你差遣。
合理地分析用户的需求，拆解任务，
视用户的要求和你的常识和判断，
协调规划4位子agent执行你划定的任务，返回你需要的信息。
注意，在时间紧迫任务中，要留有余量，例如，火车站进站应预留20分种，出站应预留15分钟，吃饭应预留一个小时。
你需要处理大量的信息，消耗相当的token量是必然的，请不要有顾虑，给用户返回一个足够详尽的出行规划吧
输出最终结果的时候，直接按照回答的格式和排版输出一个html文件
当用户告诉你他的习惯或者偏好时，将他们保存到 /memories/AGENTS.md ，以便能在将来与用户的交互中达成默契。
"""

conn_string =  "postgresql://postgres:your_passwd_here_for_postgres@localhost:5432/postgres"



os.environ["LANGGRAPH_STRICT_MSGPACK"] = "true"
thread_id_config = {"configurable" : {"thread_id" : "1"}}
async def invoke_main_agent(input):
    async with AsyncSqliteSaver.from_conn_string("agent_memory.sqlite") as thread_checkpoint:
        async with AsyncPostgresStore.from_conn_string(conn_string) as store:
            await store.setup()
            
            await store.aput(
                ("tour_agent",),
                "/memories/AGENTS.md",
                create_file_data( """ ### User Preference Recorded here.
                                 """),
            )

            main_agent = create_deep_agent(
                model = init_chat_model(
                    model = "you_llm_providers_model_name",
                    api_key = MAIN_AGENT_LLM_API_KEY,
                ),
                system_prompt = main_agent_system_prompt,
                subagents= subagents,
                checkpointer= thread_checkpoint,
                memory=["/memories/AGENTS.md"],
                backend=CompositeBackend(
                    default=StateBackend(),                        
                    routes={
                        "/memories": StoreBackend(                 
                            store=store,                           
                            namespace=("tour_agent",),           
                        ),
                    },
                ),
                store = store,
            )
            agent_response_async = await main_agent.ainvoke(
                input = input,
                config = thread_id_config,
            )
            return agent_response_async


######################################### run #########################################

user_message = """
"""

user_message = input("请输入你的旅游规划详细要求，或者其他任何你想跟agent说的话：")

input = {
            "messages" :[ 
                {
                    "role" : "user" , 
                    "content" : user_message,
                }
            ]
        }

agent_response = asyncio.run( invoke_main_agent(input = input) )

with open("output_from_main_agent.py","w",encoding = "utf-8") as f:
    f.write(str(agent_response))

with open("output_from_main_agent.html","w",encoding = "utf-8") as f:
    f.write(agent_response["messages"][-1].content)

print("\n")
print("_" * 50)
print("写入已完成。")
print("\n")
print("_" * 50)
print(agent_response["messages"][-1].additional_kwargs["reasoning_content"])

