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
  index = 0
	support.show()
	file_name = 'report_' + current_date.strftime("%d%m%Y_%H%M%S")
	support.save(file_name)