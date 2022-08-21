from PIL import Image, ImageDraw, ImageFont
import datetime
import locale

LINE_HEIGHT = 70

def generate(flights: dict):
  locale.setlocale(locale.LC_ALL, 'fr_FR')
  current_date = datetime.datetime.now()
  month_name = current_date.strftime("%B").capitalize()
  year = current_date.year;

  support = Image.open('./resources/support.png')
  canva = ImageDraw.Draw(support)
  font_path = './resources/gloria_hallelujah/gloriahallelujah.ttf'
  subtitle_font = ImageFont.truetype(font_path, 32)
  list_font = ImageFont.truetype(font_path, 36)
  canva.text((453, 101), month_name + str(year), font=subtitle_font, fill=(0,0,0))

  first_item_start = 237

  index = 0
  for key, value in flights.items():
    if (value == 0.0):
      continue
    canva.text((155, first_item_start + (index * LINE_HEIGHT)), str(index + 1) + '. ' + key + " : " + format(value, ".2f") + " tonnes", font=list_font, fill=(0,0,0)) 
    index += 1

  support.show()