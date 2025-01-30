import os
import aiohttp
import asyncio
from aiocache import cached
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from nonebot import on_request
from nonebot.plugin import PluginMetadata
from nonebot.params import CommandArg
from nonebot import on_command, get_driver, logger
from nonebot.adapters.onebot.v11 import (
    GroupIncreaseNoticeEvent, GroupRequestEvent, GroupMessageEvent, Message, Bot
)


# 加载 .env 文件
load_dotenv()

# 从 .env 文件中获取允许的群号
ALLOWED_GROUPS = set(map(int, os.getenv('ALLOWED_GROUPS', '').split(',')))

requests: dict = {}
request_matcher = on_request()

banstatus = on_command("player",aliases={"ban状态"},priority=5, block=True)

# ban状态描述
status_descriptions = {
    0: "未处理", 1: "石锤", 2: "待自证", 3: "MOSS自证", 4: "无效举报",
    5: "讨论中", 6: "等待确认", 7: "空", 8: "刷枪", 9: "上诉", 'None': "无记录", 'null': "无记录",
}

#异步获取josn数据
async def fetch_json(session: aiohttp.ClientSession, url: str, timeout: int = 20) -> Optional[Dict[str, Any]]:
    try:
        async with session.get(url, timeout=timeout) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        return None
    
# 获取玩家数据
async def get_playerdata(session: aiohttp.ClientSession, playername: str) -> Optional[Dict[str, Any]]:
    server_url = f"https://api.gametools.network/bfv/stats/?format_values=true&name={playername}&platform=pc&skip_battlelog=false&lang=zh-cn"
    data = await fetch_json(session, server_url)
    return data

# 获取玩家ID
@cached(ttl=600)
async def get_persona_id(session: aiohttp.ClientSession, username: str) -> Optional[str]:
    url_uid = f"https://api.bfvrobot.net/api/v2/bfv/checkPlayer?name={username}"
    user_data = await fetch_json(session, url_uid)
    if user_data and user_data.get("status") == 1 and user_data.get("message") == "successful":
        print(user_data)
        persona_id=user_data.get("data", {}).get("personaId")
        name=user_data.get("data", {}).get("name")
        user_data={"personaId":persona_id,"name":name}
        return user_data 

# 获取ban状态
@cached(ttl=600)
async def get_ban_data(session: aiohttp.ClientSession, persona_id: str) -> Optional[Dict[str, Any]]:
    url_ban = f"https://api.bfban.com/api/player?personaId={persona_id}"
    return await fetch_json(session, url_ban)


# 获取社区状态
async def get_community_status(session: aiohttp.ClientSession, persona_id: str) -> Optional[Dict[str, Any]]:
    url = f"https://api.bfvrobot.net/api/player/getCommunityStatus?personaId={persona_id}"
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.json()
    
#获取所有状态
async def communitystatus(name: str) -> Optional[str]:
   async with aiohttp.ClientSession() as session: 
       userdata = await get_persona_id(session, name)
       if userdata is None:
              return "无法获取到数据"
       else:
        persona_id = userdata.get("personaId")
        playername = userdata.get("name")
        bandata = await get_ban_data(session, persona_id) #处理联ban状态
        robotdata =  await get_community_status(session, persona_id) #处理bfvrobot状态
        if bandata is None:
                banstat = "无记录"
        else:
                status = bandata.get("data", {}).get("status")
                # 处理 None 和 'null'
                if status is None or status == 'null':
                    banstat = "无记录" 
                else:
                    banstat = status_descriptions.get(status, "未知状态😭")
        robotstat = robotdata.get("data",{}).get("operationStatusName","未知😰")                         
        robotstatreasons = robotdata.get("data",{}).get("reasonStatusName","未知😡")
        communitystatus = (f"\n以下是查询到该玩家的游戏状态🤓\nEAID:{playername}\nPID:{persona_id}\nbfban状态：{banstat}\n机器人服游戏状态：{robotstat}\n机器人服数据库状态：{robotstatreasons}\nCiallo~(∠・ω< )⌒★")   
        return communitystatus

@request_matcher.handle()
async def handle_request(bot: Bot, event: GroupRequestEvent):
    if event.group_id in ALLOWED_GROUPS:
        _, user_name = event.comment.split('\n')
        user_name = user_name.lstrip('答案：')  # 将玩家id获取为user_name
        async with aiohttp.ClientSession() as session:
            userdata = await get_playerdata(session, user_name)  # 查询玩家数据
            if userdata is not None:
            # 提取数据
                user_name = userdata.get('userName', '未知')
                rank = userdata.get('rank', '未知')
                accuracy = userdata.get('accuracy', '未知')
                headshots = userdata.get('headshots', '未知')
                killDeath = userdata.get('killDeath', '未知')
                infantryKillsPerMinute = userdata.get('infantryKillsPerMinute', '未知')
                extracted_data = {
                "等级": rank,
                "命中率": accuracy,
                "爆头率": headshots,
                "KD": killDeath,
                "KP": infantryKillsPerMinute,
                }
                communityatatus_data = await communitystatus(user_name)  
                extracted_data_str = "\n".join([f"{key}: {value}" for key, value in extracted_data.items()])
                await request_matcher.finish(f"欢迎来到本群组\n查询到{user_name}的基础数据如下：\n{extracted_data_str}\n{communityatatus_data}")


@banstatus.handle()
async def handle_banstatus(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    name = str(arg)
    communitystatus_data = await communitystatus(name)
    await banstatus.finish(communitystatus_data) #返回查询到的状态