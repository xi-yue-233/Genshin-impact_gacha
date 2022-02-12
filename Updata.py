import math

import requests
from PIL import Image,ImageFont,ImageDraw,ImageMath
from io import BytesIO

import httpx
import asyncio
import re
import os
import json



FILE_PATH = os.path.dirname(__file__)
ICON_PATH = os.path.join(FILE_PATH,'icon')
BACK_PATH = os.path.join(FILE_PATH,'background')

WEAPON_API=  "https://wiki.biligame.com/ys/%E6%AD%A6%E5%99%A8%E5%9B%BE%E9%89%B4"
POOL_API =   "https://webstatic.mihoyo.com/hk4e/gacha_info/cn_gf01/gacha/list.json"
ROLES_API = ['https://genshin.honeyhunterworld.com/db/char/characters/?lang=CHS',
             'https://genshin.honeyhunterworld.com/db/char/unreleased-and-upcoming-characters/?lang=CHS']
ARMS_API =  ['https://genshin.honeyhunterworld.com/db/weapon/sword/?lang=CHS',
             'https://genshin.honeyhunterworld.com/db/weapon/claymore/?lang=CHS',
             'https://genshin.honeyhunterworld.com/db/weapon/polearm/?lang=CHS',
             'https://genshin.honeyhunterworld.com/db/weapon/bow/?lang=CHS',
             'https://genshin.honeyhunterworld.com/db/weapon/catalyst/?lang=CHS']
ROLES_HTML_LIST = None
ARMS_HTML_LIST = None


POOL_PROBABILITY = {
    # 所有卡池的4星和5星概率,这里直接填写官方给出的概率，程序会自动对4星概率进行累计
    "角色up池": {"5": 0.006, "4": 0.051},
    "武器up池": {"5": 0.007, "4": 0.060},
    "常驻池": {"5": 0.006, "4": 0.051}
}

UP_PROBABILITY = {
    # 这里保存的是当UP池第一次抽取到或上次已经抽取过UP时，本次出现UP的概率有多大，常驻池不受影响
    "角色up池": 0.5,
    "武器up池": 0.75
}

POOL = {
    # 这个字典记录的是3个不同的卡池，每个卡池的抽取列表
    '角色up池': {
        '5_star_UP': [],
        '5_star_not_UP':[],
        '4_star_UP': [],
        '4_star_not_UP':[],
        '3_star_not_UP':[]
    },

    '武器up池': {
        '5_star_UP': [],
        '5_star_not_UP':[],
        '4_star_UP': [],
        '4_star_not_UP':[],
        '3_star_not_UP':[]
    },

    '常驻池': {
        '5_star_UP': [],
        '5_star_not_UP':[],
        '4_star_UP': [],
        '4_star_not_UP':[],
        '3_star_not_UP':[]
    }
}

DISTANCE_FREQUENCY = {
    # 3个池子的5星是多少发才保底
    '角色up池': 90,
    '武器up池': 80,
    '常驻池': 90
}

def transparent_back(img,mask):
    mask = mask.convert('RGBA')
    L, H = mask.size
    color_0 = mask.getpixel((0,0))
    mask_list=[]
    for h in range(H):
        for l in range(L):
            dot = (l,h)
            color_1 = mask.getpixel(dot)
            if color_1 == color_0:
                mask_list.append(dot)
    for dot in mask_list:
        color_1 = color_1[:-1] + (0,)
        img.putpixel(dot, color_1)
    return img

async def get_url_data(url):
    # 获取url的数据
    async with httpx.AsyncClient() as client:
        resp = await client.get(url=url)
        if resp.status_code != 200:
            raise ValueError(f"从 {url} 获取数据失败，错误代码 {resp.status_code}")
        return resp.content

async def get_character_list():
    # 从 genshin.honeyhunterworld.com 获取角色列表并更新
    global ROLES_HTML_LIST
    if ROLES_HTML_LIST == None:
        ROLES_HTML_LIST = []
        for api in ROLES_API:
            data = await get_url_data(api)
            ROLES_HTML_LIST.append(data.decode("utf-8"))

    characters_list={}
    character_5_star=[]
    character_4_star = []
    pattern = "char_sea_cont><a href=.{3000}"
    for html in ROLES_HTML_LIST:
        txt = re.findall(pattern, html)
        if txt == None:
            continue
        else:
            for data in txt:
                 data=str(data).replace("<svg class=sea_char_stars width=30 height=30><path d=\"M 15.000 21.000 L 22.053 24.708 L 20.706 16.854 L 26.413 11.292 L 18.527 10.146 L 15.000 3.000 L 11.473 10.146 L 3.587 11.292 L 9.294 16.854 L 7.947 24.708 L 15.000 21.000\" stroke=#000 stroke-width=1 fill=yellow /></svg>","")
                 CH_name= re.search('<span class=sea_charname>.+</span>', data).group()
                 CH_name=CH_name[25:-7]

                 En_name = re.search('/char/.+/\?lang=CHS', data).group()
                 En_name = En_name[6:En_name.index("/?lang=CHS\"")]

                 # 获取角色属性、星数
                 element = re.search('/img/icons/element/.+?_35.png', data).group()
                 element = element[19:-7]

                 star = data.count('<div class=sea_char_stars_wrap>')

                 if CH_name != "旅行者" and CH_name != "埃洛伊":
                     if star==5:
                         character_5_star.append(CH_name)
                     else:
                         character_4_star.append(CH_name)
                     role_name_path = os.path.join(ICON_PATH, "角色图鉴", CH_name + ".png")
                     if os.path.exists(role_name_path):
                         continue
                     elif not os.path.exists(role_name_path):
                         print("正在更新", CH_name, "的信息")
                         role_icon = await paste_role_icon(En_name,element,star)
                         with open(role_name_path, "wb") as icon_file:
                             role_icon.save(icon_file)
    characters_list["5_star"]=character_5_star
    characters_list["4_star"]=character_4_star
    return characters_list

async def get_weapon_info():
    url = WEAPON_API
    params = {}
    res = requests.get(url=url,params=params)
    pattern='<tr class="divsort" data-param1=\"[\\u4e00-\\u9fa5]+\" +data-param2=\"[0-9]+\" +data-param3=\"[^.]+\"'
    match_list=re.findall(pattern,res.text)
    weapon_map={}
    weapon_5_star=[]
    weapon_4_star = []
    weapon_3_star=[]
    for match in match_list:
        match=str(match)
        star=match[match.index("data-param2=\"")+len("data-param2=\""):match.index("\" data-param3=")]
        statute=match[match.index("data-param1=\"")+len("data-param1=\""):match.index("\" data-param2=")]
        try:
            get_method = match[match.index("data-param5=\"") + len("data-param5=\""):match.index("\" data-param6=")]
            weapon_name=match[match.index("title=\"")+len("title=\""):match.index("\"><img")]
        except:
            continue
        if get_method.find("祈愿") and get_method.find("限定祈愿"):
            continue

        if star == '5':
            weapon_5_star.append(weapon_name)
        elif star == '4':
            weapon_4_star.append(weapon_name)
        else:
            weapon_3_star.append(weapon_name)
        weapon_name_path = os.path.join(ICON_PATH, "武器图鉴", weapon_name + ".png")
        if os.path.exists(weapon_name_path):
            continue
        elif not os.path.exists(weapon_name_path):
            print("正在更新", weapon_name, "的信息")
            weapon_id=await get_arm_id(weapon_name)
            role_icon = await paste_weapon_icon(weapon_id, statute, star)
            with open(weapon_name_path, "wb") as icon_file:
                role_icon.save(icon_file)
    weapon_map["5_star"]=weapon_5_star
    weapon_map["4_star"] = weapon_4_star
    weapon_map["3_star"] = weapon_3_star
    return weapon_map


async def get_arm_id(ch_name):
    # 从 genshin.honeyhunterworld.com 获取武器的ID
    global ARMS_HTML_LIST
    if ARMS_HTML_LIST == None:
        ARMS_HTML_LIST = []
        for api in ARMS_API:
            data = await get_url_data(api)
            ARMS_HTML_LIST.append(data.decode("utf-8"))

    pattern = '.{40}' + str(ch_name)
    for html in ARMS_HTML_LIST:
        txt = re.search(pattern, html)
        if txt == None:
            continue
        txt = re.search('weapon/.+?/\?lang', txt.group()).group()
        arm_id = txt[7:-6]
        return arm_id
    raise NameError(f"没有找到武器 {ch_name} 的 ID")


async def get_icon(url):
    # 获取角色或武器的图标，直接返回 Image
    icon = await get_url_data(url)
    icon = Image.open(BytesIO(icon))
    icon_a = icon.getchannel("A")
    icon_a = ImageMath.eval("convert(a*b/256, 'L')", a=icon_a, b=icon_a)
    icon.putalpha(icon_a)
    return icon

async def paste_role_icon(en_name,element,star):
    # 拼接角色图鉴图
    url = f"https://genshin.honeyhunterworld.com/img/char/{en_name}_gacha_card.png"
    avatar_icon = await get_icon(url)
    element_path = os.path.join(FILE_PATH, 'background', f'{element}.png')
    element_icon = Image.open(element_path)
    bg = Image.open(os.path.join(FILE_PATH,'background',f'{star}star_back.png')).convert('RGBA')
    star_image = Image.open(os.path.join(FILE_PATH,'background',f'{star}_star.png')).convert('RGBA')

    im = Image.new("RGBA", (213, 1440), (0, 0, 0,0))

    dtbox1 = (0, 0)
    im.paste(bg, dtbox1,mask=bg.split()[3])

    if avatar_icon.height>1000:
        avatar_icon=avatar_icon.resize((280, math.ceil(280/(avatar_icon.width/avatar_icon.height))))
        dtbox1 = (-45, 267)
    else:
        avatar_icon=avatar_icon.resize((300, math.ceil(300/(avatar_icon.width/avatar_icon.height))))
        dtbox1 = (-45, 330)
    im.paste(avatar_icon, dtbox1,mask=avatar_icon.split()[3])

    mask = Image.open(os.path.join(FILE_PATH, 'background', 'mask.png')).convert('RGBA')

    im=transparent_back(im,mask)

    dtimg1=Image.open(os.path.join(FILE_PATH, 'background', f'{star}star_back_mask.png')).convert('RGBA')
    dtbox1 = (0, 0)
    im.paste(dtimg1, dtbox1,mask=dtimg1.split()[3])

    dtbox1 = (32, 1060)
    im.paste(star_image, dtbox1,mask=star_image.split()[3])

    dtbox1 = (43, 920)
    element_icon=element_icon.resize((128,128))
    im.paste(element_icon, dtbox1,mask=element_icon.split()[3])

    return im

async def paste_weapon_icon(id,type,star):
    # 拼接武器图鉴图
    url = f"https://genshin.honeyhunterworld.com/img/weapon/{id}_gacha.png"
    avatar_icon = await get_icon(url)
    type_path = os.path.join(FILE_PATH, 'background', f'{type}.png')
    type_icon = Image.open(type_path)
    bg = Image.open(os.path.join(FILE_PATH,'background',f'{star}star_back.png')).convert('RGBA')
    star_image = Image.open(os.path.join(FILE_PATH,'background',f'{star}_star.png')).convert('RGBA')

    im = Image.new("RGBA", (213, 1440), (0, 0, 0,0))

    dtbox1 = (0, 0)
    im.paste(bg, dtbox1,mask=bg.split()[3])

    if avatar_icon.width>500:
        avatar_icon=avatar_icon.resize((550, math.ceil(550/(avatar_icon.width/avatar_icon.height))))
        dtbox1 = (-170, 200)
    elif avatar_icon.height-avatar_icon.width<100:
        avatar_icon = avatar_icon.resize((240, math.ceil(240 / (avatar_icon.width / avatar_icon.height))))
        dtbox1 = (-20, 600)
    elif avatar_icon.width<200:
        avatar_icon=avatar_icon.resize((180, math.ceil(180/(avatar_icon.width/avatar_icon.height))))
        dtbox1 = (20, 390)
    else:
        avatar_icon=avatar_icon.resize((240, math.ceil(240/(avatar_icon.width/avatar_icon.height))))
        dtbox1 = (-20, 350)
    im.paste(avatar_icon, dtbox1,mask=avatar_icon.split()[3])

    mask = Image.open(os.path.join(FILE_PATH, 'background', 'mask.png')).convert('RGBA')

    im=transparent_back(im,mask)

    dtimg1=Image.open(os.path.join(FILE_PATH, 'background', f'{star}star_back_mask.png')).convert('RGBA')
    dtbox1 = (0, 0)
    im.paste(dtimg1, dtbox1,mask=dtimg1.split()[3])

    dtbox1 = (32, 1060)
    im.paste(star_image, dtbox1,mask=star_image.split()[3])

    dtbox1 = (43, 920)
    type_icon=type_icon.resize((128,128))
    im.paste(type_icon, dtbox1,mask=type_icon.split()[3])

    return im


async def up_arm_icon(name, star):
    # 更新武器图标
    arm_name_path = os.path.join(ICON_PATH, "武器图鉴", str(name) + ".png")
    if os.path.exists(arm_name_path):
        return
    if not os.path.exists(os.path.join(ICON_PATH, '武器图鉴')):
        os.makedirs(os.path.join(ICON_PATH, '武器图鉴'))




async def init_pool_list():
    # 初始化卡池数据
    global ROLES_HTML_LIST
    global ARMS_HTML_LIST
    global POOL

    ROLES_HTML_LIST = None
    ARMS_HTML_LIST = None

    data = await get_url_data(POOL_API)
    data = json.loads(data.decode("utf-8"))
    for d in data["data"]["list"]:
        if d['gacha_name'] == "角色":
            pool_name = '角色up池'
        elif d['gacha_name'] == "武器":
            pool_name = '武器up池'
        else:
            pool_name = '常驻池'

        pool_url = f"https://webstatic.mihoyo.com/hk4e/gacha_info/cn_gf01/{d['gacha_id']}/zh-cn.json"
        pool_data = await get_url_data(pool_url)
        pool_data = json.loads(pool_data.decode("utf-8"))

        #获取up卡池信息
        for prob_list in ['r3_prob_list','r4_prob_list','r5_prob_list']:
            for i in pool_data[prob_list]:
                item_name = i['item_name']
                item_type = i["item_type"]
                item_star = str(i["rank"])
                key = ''
                key += item_star
                if str(i["is_up"]) == "1":
                    key += "_star_UP"
                else:
                    key += "_star_not_UP"
                POOL[pool_name][key].append(item_name)

    character_list=await get_character_list()
    weapon_list=await get_weapon_info()
    character_list=json.dumps(character_list,ensure_ascii=False)
    weapon_list = json.dumps(weapon_list,ensure_ascii=False)
    POOL=json.dumps(POOL,ensure_ascii=False)

    f1 = open("character_data.json", "w+")
    f2=open("weapon_data.json","w+")
    f3=open("now_up.json","w+")

    f1.write(character_list)
    f2.write(weapon_list)
    f3.write(POOL)

    f1.close()
    f2.close()
    f3.close()
    """
    if item_type == '角色':
        await up_role_icon(name = item_name,star = item_star)
    else:
        await up_arm_icon(name = item_name,star = item_star)
    """



# 初始化
loop = asyncio.get_event_loop()
loop.run_until_complete(init_pool_list())
