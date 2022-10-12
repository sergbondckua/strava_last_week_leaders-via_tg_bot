import os
from urllib.request import urlopen
from PIL import (
    Image,
    ImageChops,
    ImageDraw,
    ImageFont
)
from pilmoji import Pilmoji
from fontTools.ttLib import TTFont

import start


def crop_to_circle(im):
    """ Создает круглую рамку для фото и обрезает делая круглой с ободком (border)"""
    big_size = (im.size[0] * 3, im.size[1] * 3)
    mask = Image.new('L', big_size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0) + big_size, fill=255)
    mask = mask.resize(im.size, Image.Resampling.LANCZOS)
    mask = ImageChops.darker(mask, im.split()[-1])
    im.putalpha(mask)
    border = Image.new("RGBA", big_size, 0)
    ImageDraw.Draw(border).ellipse((0, 0) + big_size,
                                   fill=0, outline="#fff", width=3)
    border = border.resize(im.size, Image.Resampling.LANCZOS)
    im.paste(border, (0, 0), border)


def char_in_font(unicode_char, font):
    """ Проверяет не поддерживает ли шрифт символ в строке, если не поддерживает True"""
    for cmap in font['cmap'].tables:
        if cmap.isUnicode():
            if ord(unicode_char) in cmap.cmap:
                return False
    return True


def get_poster_leaders(list_data_leaders):
    """ Создает готовые изображения со списком лидеров"""

    # Формируем изображение и его фон
    crossrunche = Image.open(os.path.join(start.BASE_DIR, 'images/crossrunche.png'))
    strava = Image.open(os.path.join(start.BASE_DIR, 'images/strava.png'))
    cup = Image.open(os.path.join(start.BASE_DIR, 'images/cup.png'))
    out = Image.open(os.path.join(start.BASE_DIR, 'images/background.png'))
    out2 = Image.open(os.path.join(start.BASE_DIR, 'images/background2.png'))

    # На фон out накладываем значки
    out.paste(cup, (130, 150), cup)
    out.paste(crossrunche, (5, 5), crossrunche)
    out.paste(strava, (538, 0), strava)

    # На фон out и out2 накладываем текст
    emoji_text = Pilmoji(out)
    emoji_text2 = Pilmoji(out2)
    ubuntu_font = os.path.join(start.BASE_DIR, 'fonts/Ubuntu-Regular.ttf')
    symbol_font = os.path.join(start.BASE_DIR, 'fonts/Symbola-AjYx.ttf')
    font = ImageFont.truetype(ubuntu_font, size=30)
    emoji_text.text((538, 240), '🔟\n🔝', font=font)
    shift = 362  # Начальная координата топ-10 списка
    shift_2 = 0  # Начальная координата после топ-10 списка

    start.logging.info('Формируются постеры с рейтингом...')

    # Данные от get_leaders_data_list и размещаем их на изображении
    for place, sportsmen in enumerate(list_data_leaders[:26]):

        # Если символы в имени (строке) спортсмена не поддерживаются шрифтом заменяем на шрифт, который это умеет
        if char_in_font(sportsmen.get('name')[:1], TTFont(ubuntu_font)):
            font = ImageFont.truetype(symbol_font, size=26)
        else:
            font = ImageFont.truetype(ubuntu_font, size=30)

        # Аватарку спортсмена уменьшаем до нужных размеров
        avatar = Image.open(urlopen(sportsmen.get('avatar_medium'))).convert('RGBA').resize((60, 60))
        avatar_top_3 = Image.open(urlopen(sportsmen.get('avatar_large'))).convert('RGBA').resize((124, 124))

        # Делаем аватарки круглыми
        crop_to_circle(avatar)
        crop_to_circle(avatar_top_3)

        # Формируем первый список изображение, ТОП10
        if place <= 9:
            if place <= 2:
                coordinate = ()
                if place == 0:  # Первое место
                    coordinate = (258, 28)
                elif place == 1:  # Второе место
                    coordinate = (130, 55)
                elif place == 2:  # Третье место
                    coordinate = (385, 60)
                out.paste(avatar_top_3, coordinate, avatar_top_3)

            out.paste(avatar, (60, shift), avatar)
            emoji_text.text((20, shift + 20),
                            f"{sportsmen.get('rank')}.",
                            font=ImageFont.truetype(ubuntu_font, size=30),
                            fill='#1b0f13'
                            )

            emoji_text.text((140, shift + 20),
                            f"{sportsmen.get('name')} 🔸 {sportsmen.get('distance')}",
                            font=font,
                            fill='#1b0f13'
                            )
            shift += 62
        # Формируем первый список изоборажение, все остальные
        else:
            out2.paste(avatar, (60, shift_2), avatar)
            emoji_text2.text((20, shift_2 + 20),
                             f"{sportsmen.get('rank')}.",
                             font=ImageFont.truetype(ubuntu_font, size=30),
                             fill='#1b0f13'
                             )

            emoji_text2.text((140, shift_2 + 20),
                             f"{sportsmen.get('name')} 🔸 {sportsmen.get('distance')}",
                             font=font,
                             fill='#1b0f13'
                             )
            shift_2 += 62
    # Сохраняем созданное изображение и закрываем
    out.save(os.path.join(start.BASE_DIR, 'images/out/out1.png'), 'PNG')
    out.close()
    # Сохраняем созданное изображение и закрываем
    out2.save(os.path.join(start.BASE_DIR, 'images/out/out2.png'), 'PNG')
    out2.close()
    start.logging.info('Постеры готовы и сохранены')
