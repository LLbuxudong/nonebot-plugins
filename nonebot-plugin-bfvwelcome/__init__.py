import os
import aiohttp
import asyncio
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from nonebot import on_request
from nonebot.plugin import PluginMetadata
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import (
    GroupIncreaseNoticeEvent, GroupRequestEvent, GroupMessageEvent, Message, Bot
)


# 加载 .env 文件
load_dotenv()

# 从 .env 文件中获取允许的群号
ALLOWED_GROUPS = set(map(int, os.getenv('ALLOWED_GROUPS', '').split(',')))

requests: dict = {}
request_matcher = on_request()
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

@request_matcher.handle()
async def handle_request(bot: Bot, event: GroupRequestEvent):
    if event.group_id in ALLOWED_GROUPS:
        _, user_name = event.comment.split('\n')
        user_name = user_name.lstrip('答案：')  # 将玩家id获取为user_name
        async with aiohttp.ClientSession() as session:
            userdata = await get_playerdata(session, user_name)  # 查询玩家数据
            # 提取数据
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
            extracted_data_str = "\n".join([f"{key}: {value}" for key, value in extracted_data.items()])
            await request_matcher.finish(f"查询到{user_name}的部分数据如下：\n{extracted_data_str}")
#TODO 增加bfban和bfvrobot查询111









