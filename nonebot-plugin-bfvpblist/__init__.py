import httpx
from typing import Any, Dict, Optional
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from nonebot import on_command
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot,MessageSegment,MessageEvent
from nonebot.params import CommandArg
import os

"""
一个简易的查询pb记录的插件
"""

BanType ={
    '0':'','1':'BFBAN石锤或即将石锤','2':'','3':'自定义原因','4':'','5':'','6':'QQ群踢人','7':'','8':'服务器规则限制Ban','9':'数据异常', #FIXME
    '10':'','11':'小电视屏蔽/踢人','12':'','13':''
}

playerpb = on_command("pb=", aliases={"屏蔽="}, priority=5, block=True)

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
    except httpx.TimeoutException as e:
        return {"error": "请求超时"}

# 获取玩家 personId
async def getplayerid(name: str):
    url = f'https://api.bfvrobot.net/api/bfv/player?name={name}'
    data = await fetch_json(url)
    return data

#获取pb记录
async def getpblist(personid: str):
    url = f'https://api.bfvrobot.net/api/player/getBannedLogsByPersonaId?personaId={personid}'
    data = await fetch_json(url)
    return data

async def create_text_image_bytes(text: str, font_path: str, font_size: int) -> BytesIO:
    """
    通过pIL创建文本图片并返回 BytesIO 字节流
    """
    # 估算图像大小（可动态计算）
    img = Image.new('RGBA', (800, 100 + (len(text.split('\n')) + 1) * (font_size + 10)), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, font_size)

    line_spacing = 10
    lines = text.split('\n')
    y = 100

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (img.width - text_width) / 2
        draw.text((x, y), line, fill=(255, 255, 255), font=font)
        y += text_height + line_spacing

    # 将图像写入 BytesIO
    byte_io = BytesIO()
    img.save(byte_io, format="PNG")
    img_bytes = byte_io.getvalue()

    return img_bytes

def format_iso_time(time_str: str, fmt: str = "%Y年%m月%d日 %H:%M:%S") -> str:
    """
    将 ISO 时间字符串转为指定格式
    
    Args:
        time_str (str): ISO 格式时间字符串
        fmt (str): 输出格式，默认是 "YYYY年MM月DD日 HH:MM:SS"
    
    Returns:
        str: 格式化后的时间字符串
    """
    # 去掉 Z 并加上时区信息以便正确解析
    dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    return dt.strftime(fmt)

@playerpb.handle()
async def handle_playerpb(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    name = arg.extract_plain_text().strip()
    datas = await getplayerid(name)
    #获取personId
    personid = datas.get('data', {}).get('personaId', None)
    name = datas.get('data', {}).get('name', None)
    if personid != None:
        print(f"玩家 {name} 的 personId 是: {personid}")
        #获取pb记录
        pblist = await getpblist(personid)
        pblist = pblist.get('data', [])
        if not pblist:
            await playerpb.finish(f"玩家 {name} 没有封禁记录")
        text = ""#pb记录初始值
        for key,value in enumerate(pblist):
            text += f"\n--- 第 {key + 1} 条封禁记录 ---\n"
            ban_type_code = str(value.get('banType'))  # 获取 banType 并转为字符串
            ban_type_desc = BanType.get(ban_type_code, '未知类型')  # 查找对应的描述
            server_name = value.get('serverName')
            reason = value.get('reason')
            expire_time = format_iso_time(value.get('createTime'))
            text +=f'服务器：{server_name}\n封禁类型: {ban_type_desc} ({ban_type_code})\n原因: {reason},\n时间: {expire_time}\n'
        font_path = os.path.join(os.path.dirname(__file__), "STXINWEI.TTF")#获取绝对路径
        image_stream = await create_text_image_bytes(text=text, font_path="STXINWEI.TTF", font_size=24)
        await bot.send(event,MessageSegment.image(image_stream),reply_message=event.message, at_sender=True)    
    else:
        await playerpb.finish(f"未找到玩家 {name}")