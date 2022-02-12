import sys

from PIL import Image,ImageSequence

import os
import json

FILE_PATH = os.path.dirname(__file__)
ICON_PATH = os.path.join(FILE_PATH,'icon')
BACK_PATH = os.path.join(FILE_PATH,'background')

def generate(qq,type):
    bg = Image.open(os.path.join(FILE_PATH, 'background', f'background.png')).convert('RGBA')

    im = Image.new("RGBA", (2560, 1440), (0, 0, 0, 0))

    dtbox1 = (0, 0)
    im.paste(bg, dtbox1, mask=bg.split()[3])
    f1=open("weapon_data.json","r")
    f2=open("character_data.json","r")
    weapon=json.loads(f1.read())
    character=json.loads(f2.read())
    f1.close()
    f2.close()
    is_5star_exists=False

    #list_c=["行秋","行秋","行秋","行秋","行秋","行秋","行秋","行秋","行秋","行秋"]

    for i in range(3,13):
        name = sys.argv[i]
        #name=list_c[i-2]
        if name in weapon["5_star"] or name in character["5_star"]:
            is_5star_exists=True
        object_name=os.path.join(ICON_PATH, '武器图鉴', f'{name}.png')
        if os.path.exists(object_name):
            pass
        else:
            object_name = os.path.join(ICON_PATH, '角色图鉴', f'{name}.png')
        object_img=Image.open(object_name).convert('RGBA')
        dtbox1=(10+(i-2)*214,0)
        im.paste(object_img,dtbox1,mask=object_img.split()[3])

    #1模式只生成静态图片，2模式生成动态抽卡图
    if type=='1':
        im.save(f"result\\{qq}.png")
    elif type=='2':
        sequence = []
        if is_5star_exists==False:
            for i in range(0, 60):
                if i < 10:
                    i = "0" + str(i)
                start_anime = Image.open(os.path.join(FILE_PATH, 'background\\4_star_sequence', f'4_star {i}.png')).convert('RGBA')
                sequence.append(start_anime)
        else:
            for i in range(0,60):
                if i<10:
                    i="0"+str(i)
                start_anime = Image.open(os.path.join(FILE_PATH, 'background\\5_star_sequence', f'5_star {i}.png')).convert('RGBA')
                sequence.append(start_anime)

        im=im.resize((960,540))
        sequence.append(im)
        sequence[0].save(f'result\\{qq}.gif', save_all=True, append_images=sequence[1:])

generate(sys.argv[1],sys.argv[2])
