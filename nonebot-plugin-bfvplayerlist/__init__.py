# -*- coding: utf-8 -*-
from nonebot import on_command
from nonebot import require
from typing import Optional, Dict, Any, Union
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment, MessageEvent
from nonebot.params import CommandArg
import httpx
from jinja2 import Environment, FileSystemLoader
import os
import base64
from nonebot.adapters import Bot
require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import html_to_pic
from nonebot.plugin import PluginMetadata
import time

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name="bfvplayerlist",
    description="查询bfv服务器玩家列表",
    usage="bfvplayerlist <服务器名称>",
    type="application",
    homepage="https://github.com/LLbuxudong/nonebot-plugin-bfvplayerlist",
    supported_adapters={"~onebot.v11"},
)

playerlist = on_command("playerlist", aliases={"玩家列表"}, priority=5, block=True)

# 异步请求 JSON 数据
async def fetch_json(url: str, timeout: int = 20) -> Optional[Dict[str, Any]]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"请求失败，状态码: {response.status_code}, 响应内容: {response.text}"}
    except httpx.RequestError as e:
        return {"error": f"请求发生错误: {e}"}

async def getservername(servername: str):
    url = f"https://api.bfvrobot.net/api/bfv/servers?serverName={servername}&region=all&limit=5&lang=zh-CN"
    data = await fetch_json(url)
    return data

async def getserverplayer(serverid: str):
    url = f"https://api.bfvrobot.net/api/bfv/players?gameId={serverid}"
    data = await fetch_json(url)
    return data

@playerlist.handle()
async def handle_server(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    start_time = time.time()  # 记录开始时间
    
    servername = arg.extract_plain_text().strip()
    servername_utf8 = servername.encode('utf-8').decode('utf-8')
    if not servername:
        await playerlist.finish("请输入要查询的服务器名称")
    else:
        serveridlist = await getservername(servername)
        if "error" in serveridlist:
            await playerlist.finish(f"查询服务器信息失败: {serveridlist['error']}")
        else:
            serveridlist = serveridlist.get("data", [])
            if not serveridlist:
                await playerlist.finish(f"未找到 {servername} 该服务器")
            elif len(serveridlist) == 1:
                serverid = serveridlist[0].get("gameId")
                if not serverid:
                    await playerlist.finish("未找到有效的服务器ID")
                serverplayerdata = await getserverplayer(serverid)
                if "error" in serverplayerdata:
                    await playerlist.finish(f"查询服务器信息失败: {serverplayerdata['error']}")
                else:
                    serverplayerdata = serverplayerdata.get("data", {})
                    
                    # 提取所需字段
                    servername = serverplayerdata.get("serverName", "")
                    serverid = serverplayerdata.get("gameId", "")
                    team_1 = serverplayerdata.get("players", {}).get("team_1", [])
                    team_2 = serverplayerdata.get("players", {}).get("team_2", [])
                    loading = serverplayerdata.get("players",[]).get("loading", [])
                    playgroundId = serverplayerdata.get("playgroundId", [])
                    spectators = serverplayerdata.get("players", {}).get("spectators", [])
                    
                    # 提取人数和总人数
                    soldier = serverplayerdata.get("slots", {}).get("Soldier", []).get("current", "未知") 
                    spectatorsnum = serverplayerdata.get("slots", {}).get("Spectator", []).get("current", "未知")
                    queue = serverplayerdata.get("slots", {}).get("Queue", []).get("current", "未知")
                    soldier_max = serverplayerdata.get("slots", {}).get("Soldier", []).get("max", "未知") #游玩
                    spectator_max = serverplayerdata.get("slots", {}).get("Spectator", []).get("max", "未知")#观战
                    queue_max = serverplayerdata.get("slots", {}).get("Queue", []).get("max", "未知") #排队
                    
                    
                    # 提取具体 ID
                    team_1_ids = [player.get("personaId") for player in team_1]
                    team_2_ids = [player.get("personaId") for player in team_2]
                    loading_ids = [player.get("personaId") for player in loading]  # 排队
                    spectators_ids = [player.get("personaId") for player in spectators]  # 观战

                    # 获取背景图片的绝对路径
                    template_path = os.path.dirname(__file__)  # 获取当前文件所在目录
                    background_image_path = os.path.join(template_path, 'background-image.jpg')
                
                    # 将背景图片转换为Base64编码
                    with open(background_image_path, 'rb') as image_file:
                        background_image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

                    # 计算花费总用时
                    elapsed_time = time.time() - start_time
                    elapsed_time_str = f"{elapsed_time:.2f} 秒"

                    # 获取 Bot 的昵称和 ID
                    bot_info = await bot.get_login_info()
                    bot_nickname = bot_info.get("nickname", "Bot")
                    bot_id = bot_info.get("user_id", "Unknown")

                    # 获取群号
                    group_id = event.group_id if isinstance(event, GroupMessageEvent) else "Unknown"

                    # 构建模板参数
                    template_param = {
                        "playgroundId": playgroundId,
                        "servername": servername,
                        "serverid": serverid,
                        "current_players": soldier,
                        "soldier_max": soldier_max,
                        "spectator_max": spectator_max,
                        "queue_max": queue_max,
                        "loading_count":queue,
                        "spectators_count":spectatorsnum,
                        "team_1": team_1,
                        "team_2": team_2,
                        "loading": loading,
                        "spectators": spectators,
                        "team_1_ids": team_1_ids,
                        "team_2_ids": team_2_ids,
                        "loading_ids": loading_ids,
                        "spectators_ids": spectators_ids,
                        "background_image": f"data:image/jpeg;base64,{background_image_base64}",
                        "elapsed_time": elapsed_time_str,
                        "bot_nickname": bot_nickname,
                        "bot_id": bot_id,
                        "group_id": group_id
                    }
                    
                    # 读取并渲染模板
                    env = Environment(loader=FileSystemLoader(template_path))
                    template = env.get_template('html.html')
                    html_content = template.render(template_param)

                    # 渲染HTML并生成图像
                    image_path = await html_to_pic(
                        html=html_content,
                        viewport={"width": 1200, "height": 1200},  # 调整视口大小以适应内容
                        wait=2,
                        type="png",
                        device_scale_factor=2
                    )

                    await bot.send(event, MessageSegment.image(image_path),reply_message=True) 

            else:
                # 处理多个服务器的情况
                await playerlist.finish("查询到的服务器过多,请指定具体服务器")