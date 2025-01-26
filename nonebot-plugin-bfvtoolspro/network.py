from httpx import AsyncClient
from typing import Optional, Dict, Any

client = AsyncClient()


async def request(url: str, params: dict, retry_count: int = 3):
    """
    异步发送HTTP请求并处理重试逻辑。

    本函数尝试向指定URL发送GET请求，并携带相关参数。如果初次请求失败，
    函数将根据重试计数进行重试。此设计确保在网络问题或服务端问题时，
    提高请求成功的概率。

    参数:
    - url (str): 目标URL地址，用于指定请求的目的地。
    - params (dict): 请求参数，以字典形式提供，附加在URL后面。
    - retry_count (int, 可选): 最大重试次数，默认为3次。当请求失败时，
      函数将重试指定次数。

    返回:
    - 如果请求成功且状态码为200，则返回响应的JSON格式数据。
    - 如果重试次数用尽仍未能成功，则返回None。
    """
    # 发起GET请求并传递参数
    response = await client.get(url, params=params)
    
    # 检查响应状态码是否为200（HTTP OK）
    if response.status_code == 200:
        # 如果响应成功，返回JSON数据
        return response.json()
    
    # 如果当前重试次数大于0，则递归重试
    if retry_count > 0:
        return await request(url, params, retry_count - 1)
    
    # 如果所有尝试均失败，则返回None
    return None


async def request_player(name: str):
    response = await request('https://api.bfvrobot.net/api/v2/bfv/checkPlayer', {'name': name}) #获取用户的{'userId': 1009845514809, 'name': 'LL-zako-zako', 'personaId': 1005021714809} 数据
    if response:
        return response.get('data')
    return response

#获取联robot服务器屏蔽原因
async def request_ban(persona_id: int):
    response = await request('https://api.bfvrobot.net/api/player/getBannedLogsByPersonaId', {'personaId': persona_id})
    return response.get('data')

