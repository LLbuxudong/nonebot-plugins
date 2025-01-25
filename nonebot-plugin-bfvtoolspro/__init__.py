import os
from dotenv import load_dotenv
from nonebot import on_request, on_notice, on_startswith
from nonebot.plugin import PluginMetadata
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import (
    GroupIncreaseNoticeEvent, GroupRequestEvent, GroupMessageEvent, Message, Bot
)

from .data import Data
from .utils import format_time
from .network import request_player, request_ban

# 加载 .env 文件
load_dotenv()

# 从 .env 文件中获取允许的群号
ALLOWED_GROUPS = set(map(int, os.getenv('ALLOWED_GROUPS', '').split(',')))

data = Data()
requests: dict = {}

notice_matcher = on_notice()
request_matcher = on_request()
query_ban_matcher = on_startswith('pb=')


@request_matcher.handle()
async def _(event: GroupRequestEvent, bot: Bot):
    # 检查是否是允许的群聊
   if event.group_id not in ALLOWED_GROUPS:
    print("未在加群列表中，自动通过")
    await bot.set_group_add_request(
          flag=event.flag, sub_type=event.sub_type, approve=True,
     #      reason="该群未启用入群审核功能，请联系管理员。"
     )
    await request_matcher.finish()
    return 
   elif event.group_id  in ALLOWED_GROUPS:
     _, user_name = event.comment.split('\n')
     user_name = user_name.lstrip('答案：')
     response = await request_player(user_name)
     print(response)
     if response is None:
        await bot.set_group_add_request(
            flag=event.flag, sub_type=event.sub_type, approve=False,
            reason='请求超时，请等待几秒钟后再次尝试。'
        )
        await request_matcher.finish()
     if response:
        data.players[user_name.lower()] = response['personaId']
        requests[event.user_id] = response.get('name', user_name)
        data.save()
        await bot.set_group_add_request(flag=event.flag, sub_type=event.sub_type, approve=True)
        await request_matcher.finish()
     await bot.set_group_add_request(
        flag=event.flag, sub_type=event.sub_type,
        approve=False, reason=F'未找到名为{user_name}的玩家！请检查输入是否正确，然后再次尝试'
     )
        # 发送“错误的ID”消息到群聊
     await bot.send_group_msg(
       group_id=event.group_id,  # 用请求的群 ID
       message=F'收到QQ：{event.user_id}的加群申请，提供的ID为：{user_name}，已自动拒绝，原因:错误的ID'
    )
     await request_matcher.finish()


@notice_matcher.handle()
async def _(event: GroupIncreaseNoticeEvent, bot: Bot):
    if event.group_id  in ALLOWED_GROUPS:
      if user_name := requests.pop(event.user_id, None):
        await bot.set_group_card(group_id=event.group_id, user_id=event.user_id, card=user_name)
        await notice_matcher.finish(F'收到QQ：{event.user_id}的加群申请，提供的ID为：{user_name}\n欢迎新人加入！已自动修改您的群名片为游戏名称')
      await notice_matcher.finish('未找到您的申请记录，请将昵称为EAid。', at_sender=True)


@query_ban_matcher.handle()
async def _(event: GroupMessageEvent, args: Message = CommandArg()):
    args = args.extract_plain_text().strip()
    if args not in data.players:
        response = await request_player(args)
        if response is None:
            await query_ban_matcher.finish('查询超时，请稍后再试。', at_sender=True)
        if not response:
            await query_ban_matcher.finish(F'未找到名为 {args} 的玩家！请检查输入是否正确，然后再次尝试。', at_sender=True)
        data.players[args.lower()] = response['personaId']
        data.save()
    response = await request_ban(data.players[args.lower()])
    if response is None:
        await query_ban_matcher.finish('查询超时，请稍后再试。', at_sender=True)
    if response:
        message_lines = [F'玩家 {args} 的封禁记录如下：']
        for index, ban_info in enumerate(response[:5]):
            message_lines.append(F'{index + 1}. 服务器 {ban_info["serverName"]}')
            message_lines.append(F'  - 时间：{format_time(ban_info["createTime"])}')
            message_lines.append(F'  - 原因：{ban_info["reason"]}')
        if len(response) > 5:
            message_lines.append('\n    —— 已自动省略更多记录 ——')
        await query_ban_matcher.finish('\n'.join(message_lines), at_sender=True)
    await query_ban_matcher.finish(F'玩家 {args} 还没有被封禁过。', at_sender=True)
