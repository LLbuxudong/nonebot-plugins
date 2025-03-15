#file:f:\nonebot\BOT\ceshiBOT\src\plugins\nonebot-plugin-bfvserver\__init__.py
# -*- coding: utf-8 -*-
import asyncio
import tempfile
from nonebot import on_command
from nonebot import require
from typing import Optional, Dict, Any, Union
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment
from nonebot.params import CommandArg
import aiohttp
import json
from jinja2 import Template,Environment, FileSystemLoader
import os
import base64
require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import (

    html_to_pic
)
from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name="bfvservermap",
    description="查询服务器信息",
    usage="服务器信息 <服务器名称>",
    homepage="https://github.com/LLbuxudong/nonebot-plugin-bfvservermap",
)

servermessage = on_command("server", aliases={"服务器信息"}, priority=5, block=True)

# 异步请求 JSON 数据
async def fetch_json(session: aiohttp.ClientSession, url: str, timeout: int = 20) -> Optional[Dict[str, Any]]:
    try:
        async with session.get(url, timeout=timeout) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        return None
    
# 获取服务器列表信息
async def get_server(session: aiohttp.ClientSession, servername: str) -> Optional[Dict[str, Any]]:
    server_url = f"https://api.gametools.network/bfv/servers/?name={servername}&platform=pc&limit=5&region=all&lang=zh-CN"
    data = await fetch_json(session, server_url)
    return data

# 获取服务器详细信息
async def get_server_info(session: aiohttp.ClientSession, servername_detail: str) -> Optional[Dict[str, Any]]:
    server_url = f"https://api.gametools.network/bfv/detailedserver/?name={servername_detail}&platform=pc&lang=zh-CN"
    data = await fetch_json(session, server_url)
    return data

@servermessage.handle()
async def handle_server(bot: Bot, event: GroupMessageEvent, arg: Message = CommandArg()):
    server_name = arg.extract_plain_text().strip()
    
    if not server_name:
        await servermessage.finish("请输入要查询的服务器名称")
    else:
        async with aiohttp.ClientSession() as session:  # 获取服务器列表信息
            serverlistdata = await get_server(session, server_name)
            
            if serverlistdata is None:
                await servermessage.finish("查询服务器信息失败，可能是网络异常，请稍后再试😥")
            
            servers = serverlistdata.get("servers", [])
            
            if not servers:
                await servermessage.finish(f"未找到包含{server_name}的服务器信息，请检查服务器名称是否正确")

            prefix_data = []  # 存储服务器列表
            for server in servers:
                prefix = server.get("prefix")
                if prefix and server_name.lower() in prefix.lower():  # 匹配服务器名
                    prefix_data.append(prefix)
            
            if len(prefix_data) == 1:  # 查询该服务器的详细信息
                servername = prefix_data[0]  # 只有一个prefix，赋值给servername
                async with aiohttp.ClientSession() as session:
                    serverdata_detail = await get_server_info(session, servername)
                if serverdata_detail is None:
                    await servermessage.finish("查询服务器信息失败，可能是网络异常，请稍后再试")   
                else:  # 获取到的详细数据为serverdata_detail
                    rendering_message = await servermessage.send("亚托利成功找到信息了哦，正在渲染图片给主人😊")
                    rendering_message_id = rendering_message["message_id"]
                    
                    # 提取字段信息
                    player_amount = serverdata_detail.get('playerAmount', 'N/A')
                    max_player_amount = serverdata_detail.get('maxPlayerAmount', 'N/A')
                    in_queue = serverdata_detail.get('inQueue', 'N/A')
                    prefix = serverdata_detail.get('prefix', 'N/A')
                    description = serverdata_detail.get('description', '无描述')
                    current_map = serverdata_detail.get('currentMap', 'N/A')
                    current_map_image = serverdata_detail.get('currentMapImage', 'N/A')
                    country = serverdata_detail.get('country', 'N/A')
                    mode = serverdata_detail.get('mode', 'N/A')
                    game_id = serverdata_detail.get('gameId', 'N/A')
                    owner_name = serverdata_detail.get('owner', {}).get('name', 'N/A')
                    teams = serverdata_detail.get('teams', {})
                    rotation_info = serverdata_detail.get('rotation', [])

                    # 获取背景图片的绝对路径
                    template_path = os.path.dirname(__file__)  # 获取当前文件所在目录
                    background_image_path = os.path.join(template_path, 'background-image.jpg')
                    
                    # 将背景图片转换为Base64编码
                    with open(background_image_path, 'rb') as image_file:
                        background_image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
                    
                    # 构建模板参数
                    template_params = {
                        "player_amount": player_amount,
                        "max_player_amount": max_player_amount,
                        "in_queue": in_queue,
                        "prefix": prefix,
                        "description": description,
                        "current_map": current_map,
                        "current_map_image": current_map_image,
                        "country": country,
                        "mode": mode,
                        "game_id": game_id,
                        "owner_name": owner_name,
                        "teams": teams,
                        "rotation_info": rotation_info,
                        "background_image": f"data:image/jpeg;base64,{background_image_base64}"  # 传递Base64编码的背景图片
                    }

                    # 读取并渲染模板
                    env = Environment(loader=FileSystemLoader(template_path))
                    template = env.get_template('server_template.html')
                    html_content = template.render(template_params)

                    # 渲染HTML并生成图像
                    image_path = await html_to_pic(
                    html=html_content,
                    viewport={"width": 500, "height": 250},
                    wait=2,
                    type="png",
                    device_scale_factor=2
                    )

                    # 撤回正在渲染图片的消息
                    await bot.delete_msg(message_id=rendering_message_id)
                    
                    # 发送图片
                    await bot.send(event, MessageSegment.image(image_path))

            elif len(prefix_data) > 1:
                servernamelist_all = "\n".join(prefix_data[:5])  # 显示最多5个服务器
                await servermessage.finish(f"查询到服务器列表(最多显示5个)：\n{servernamelist_all}\n当前查询到的服务器较多，请输入准确的服务器名称")