#!/usr/bin/python3

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import sys
import requests
import time
import datetime
import locale
import csv
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import geopy.distance
import smtplib
from PIL import Image, ImageDraw, ImageFont
import datetime
import locale
import consts
from logger import Logger
import re

script_path = os.getcwd()
print(script_path)
headless_instagram = False  # hide Instagram browsing
test_mode = True

# Browser params
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
options = Options() # first instance of browser -> Instagram
if headless_instagram: options.add_argument("--headless")
options.add_argument("--lang=fr-FR")
options.set_preference('intl.accept_languages', 'fr-FR')

def config():
	locale.setlocale(locale.LC_ALL, 'fr_FR')
	config_file = 'config.json'

	global current_datetime, logs_directory, output_directory, aircrafts, instagram_info, mail_info, start_days_ago, end_days_ago, gecko_driver_path, firefox_profile_path, hashtags, api_url, airports

	with open(f'./{config_file}', 'r+', encoding='utf-8') as f:
		config = json.load(f)
		logs_directory = config["logs_directory"]
		output_directory = config["output_directory"]
		aircrafts = config["aircrafts"]
		instagram_info = config["instagram"]
		mail_info = config["mail"]
		gecko_driver_path = config["gecko_driver_path"]
		firefox_profile_path = config["firefox_profile_path"]
		hashtags = config["hashtags"]
		api_url = config["api_url"]

	today = datetime.date.today()
	current_datetime = datetime.datetime.now()
	start_days_ago = (today - datetime.date(today.year, today.month, 1)).days
	end_days_ago = 0
	Logger.log_file_path = logs_directory + "/" + "log_" + current_datetime.strftime("%d%m%Y_%H%M%S") + ".txt"

	with open("resources/airports.csv") as f:
		airports = list()
		data = csv.DictReader(f)
		for d in data:
			airports.append(d)

	Logger.info('Configuration loaded.')


def check_config():
	for aircraft in aircrafts:
		if aircraft["ton_per_km"] == "":
			Logger.warning(f"""No evaluation for aircraft {aircraft["registry"]} owned/operated by {aircraft["owner_or_operator"]}""")

	if len(hashtags) == 0:
		Logger.warning("No hashtags will be added to the Instagram post.")

	if instagram_info["username"] == "" or instagram_info["password"] == "":
		Logger.error("Incomplete info for Instagram connection.")
		sys.exit()

	if mail_info["smtp_addr"] == "" or mail_info["smtp_port"] == "" or mail_info["email"] == "" or mail_info["password"] == "":
		Logger.error("Incomplete info for email.")
		sys.exit()

	if start_days_ago == "":
		Logger.error("No value for 'start_days_ago'.")
		sys.exit()

	if end_days_ago == "":
		Logger.error("No value for 'end_days_ago'.")
		sys.exit()

	if gecko_driver_path == "":
		Logger.error("No value for 'gecko_driver_path'.")
		sys.exit()
	elif not os.path.isfile(gecko_driver_path):
		Logger.error("Wrong path for 'gecko_driver_path'.")
		sys.exit()

	if firefox_profile_path == "":
		Logger.warning("No value for 'firefox_profile_path'.")
	elif not os.path.isdir(firefox_profile_path):
		Logger.warning("Wrong path for 'firefox_profile_path'.")
		sys.exit()


def generate(flights: dict):
	month_name = current_datetime.strftime("%B").capitalize()
	year = current_datetime.year;
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
		canva.text((155, first_item_start + (index * consts.LINE_HEIGHT)), str(index + 1) + '. ' + key + " : " + format(value, ".2f") + " tonnes", font=list_font, fill=(0,0,0)) 
		index += 1
		
	support.show()
	file_name = 'report_' + current_datetime.strftime("%d%m%Y_%H%M%S") + '.png'
	save_path = output_directory + "/" + file_name
	support.save(save_path)
	
	return save_path


def send_log_by_mail(nb_flights_found):
	with open(Logger.log_file_path, "r+", encoding="utf-8") as f:
		log = f.read()

	message_text = """\
	""" + str(nb_flights_found) + """ vols


	Début: """ + str(datetime.datetime.fromtimestamp(start_time).strftime("%H.%M:%S")) + """
	Fin: """ + str(datetime.datetime.fromtimestamp(end_time).strftime("%H.%M:%S")) + """


	Log:

	""" + log

	msg = MIMEMultipart()
	msg['Subject'] = "Récapitulatifs vols - " + str(datetime.date.today())
	msg['From'] = mail_info["email"]
	msg['To'] = mail_info["email"]

	msg.attach(MIMEText(message_text, "plain", "utf-8"))

	with smtplib.SMTP_SSL(mail_info["smtp_addr"], mail_info["smtp_port"]) as server:
		server.ehlo()
		server.login(mail_info["email"], mail_info["password"])
		server.sendmail(mail_info["email"], mail_info["email"], msg.as_string())

def get_flights_info():
	begin = int(start_time - start_days_ago*24*60*60)
	end = int(start_time - end_days_ago*24*60*60)
	nb_flights_found = 0
	co2_per_aircraft = {}

	for aircraft in aircrafts:
		if aircraft["ton_per_km"] == "":
			continue

		requestURL = api_url + '?icao24=' + aircraft["icao24"] + '&begin=' + str(begin) + '&end=' + str(end) 
		# Requesting API
		for i in range(20):
			try:
				Logger.info('Requesting OpenSky Network API')
				r = requests.get(requestURL, headers=headers,timeout=10)
			except:
				Logger.warning('Cannot access OpenSky Network API, sleep for 1min')
				r = None
				time.sleep(60)
			else:
				break

		if r is None :
			Logger.error('Cannot reach OpenSky API - just re-run the script')
			flights = []
		else:
			flights = r.json()

		nb_flights_found += len(flights)

		if (not aircraft["owner_or_operator"] in co2_per_aircraft):
			co2_per_aircraft[aircraft["owner_or_operator"]] = 0.0


		# Getting flights
		for flight in flights:
			if (flight['estDepartureAirport'] is None or flight['estArrivalAirport'] is None or flight['firstSeen'] is None or flight['estDepartureAirport'] == flight['estArrivalAirport']):
				continue

			departure_coord = 0
			arrival_coord = 0

			# Getting airport municipalities and day of travel
			for airport in airports:
				if (airport['ident'] == flight['estDepartureAirport'] or airport['gps_code'] == flight['estDepartureAirport']):
					departure = airport['municipality']
					departure_coord = [airport['latitude_deg'],airport['longitude_deg']]
				if (airport['ident'] == flight['estArrivalAirport'] or airport['gps_code'] == flight['estArrivalAirport']):
					arrival = airport['municipality']
					arrival_coord = [airport['latitude_deg'],airport['longitude_deg']]

				departure_time = str(datetime.date.fromtimestamp(flight['firstSeen']).strftime("%d.%m.%Y"))
				duration = flight['lastSeen'] - flight['firstSeen']

			try:
				distance = geopy.distance.geodesic(departure_coord, arrival_coord).km
			except ValueError:
				#print("AICRAFT IS " + aircraft["icao24"] + " - " + aircraft["owner_or_operator"])
				Logger.error(f'AIRCRAFT: {aircraft["icao24"]}-{aircraft["owner_or_operator"]} DEPARTURE: {flight["estDepartureAirport"]} - {departure_coord}, ARRIVAL: {flight["estArrivalAirport"]} - {arrival_coord}')
			else:
				co2 = round(distance * float(aircraft["ton_per_km"]), 1)
				co2_per_aircraft[aircraft["owner_or_operator"]] += co2

	return co2_per_aircraft, nb_flights_found


def post_on_instagram(nb_flights_found, report_path):
	if nb_flights_found != 0:
		again = 0
		# Go to Instagram
		Logger.info("Go to Instagram")
		driver = webdriver.Firefox(service=Service(gecko_driver_path), options=options)
		driver.get('https://instagram.com')
		time.sleep(5)
		
		# Log in only if sessionId did not work (looking for publish button)
		try:
			driver.find_element(By.XPATH, '//*[@class="_abl- _abm2"]')
		except:
			again = 0
			while (again < 10):
				Logger.warning("Not logged, get instagram")
				if (re.search("Allow the use of cookies", driver.page_source) or re.search("utilisation des cookies", driver.page_source)):
					allowCookiesButton = driver.find_element(By.XPATH, '//*[@class="aOOlW  bIiDR  "]').click()
					time.sleep(5)
					Logger.info("Closed cookie pop-up")
				usernameInput = driver.find_element(By.XPATH, '//*[@name="username"]').send_keys(instagram_info["username"])
				passwordInput = driver.find_element(By.XPATH, '//*[@name="password"]').send_keys(instagram_info["password"])
				loginButton = driver.find_element(By.XPATH, '//*[@type="submit"]').click()
				Logger.info("Sent login details to Instagram")
				time.sleep(5)
				if (re.search("Forgot password", driver.page_source)):
					Logger.error('Cannot log into Instagram, sleep for 2min')
					time.sleep(120)
					driver.get('https://google.com') #reload by changing page
					driver.get('https://instagram.com')
					again += 1
				else:
					again = 99
					Logger.info("Logged in Instagram")
		else:	
			again = 99
			Logger.info("Logged in Instagram")
			if (re.search("Not Now", driver.page_source) or re.search("Plus tard", driver.page_source)):
				notNowCookieButton = driver.find_element(By.XPATH, '//*[@class="aOOlW   HoLwm "]').click()

		if (again == 10):
			Logger.error("Could not log into Instagram - just re-run script later")
		else:
				# Add flight to Instagram
				again = 0
				while (again < 10):
					hashtagSample = ""
					for hashtag in hashtags:
						hashtagSample += "#" + hashtag + " "

					# Publish image
					try:
						Logger.info("Adding report to Instagram")
						time.sleep(2)
						try:
							driver.find_element(By.XPATH, "//div[contains(@class, '_a9-z')]//button[contains(@class, '_a9-- _a9_1')]").click()
							Logger.info("Refused desktop notifications")
						except:
							Logger.warning("Notifications request not found. Retry.")

						newPostButton = driver.find_element(By.XPATH, '//*[@aria-label="Nouvelle publication"]').click()
						Logger.info("New post window opened")
						time.sleep(5)
						dropZone = driver.find_element(By.XPATH, "//div[contains(@class,'_ac2r')]//input[contains(@type,'file')]").send_keys(script_path + "/" + report_path)
						Logger.info	("Report image dropped in drop zone.")
						time.sleep(8)
						submitButton = driver.find_element(By.XPATH, "//div[contains(@class,'_ab8w  _ab94 _ab99 _ab9f _ab9m _ab9p  _ab9- _abaa')]//button[contains(@type,'button')]").click()
						Logger.info("Uploaded report to Instagram, waiting for publishing.")
						time.sleep(8)
						noFilterButton = driver.find_element(By.XPATH, "//div[contains(@class,'_ab8w  _ab94 _ab99 _ab9f _ab9m _ab9p  _ab9- _abaa')]//button[contains(@type,'button')]").click()
						Logger.info("Next no filter clicked.")
						time.sleep(5)
						
						caption_area = driver.find_element(By.XPATH, '//*[@class="_ablz _aaeg"]')
						caption = (f'Classement {current_datetime.strftime("%B").capitalize()} {current_datetime.year}\n'
						'Pour plus de détails : https://github.com/celuiquialaplusgrosse/celuiquialaplusgrosse/blob/main/logs.txt\n'
						'.\n'
						'.\n'
						'.\n'
						'.\n'
						'.\n'
						f'{hashtagSample}')
					
						caption_area.send_keys(caption)
						Logger.info(f"Instagram post caption is: {caption}")
						
						Logger.info("Caption sent")						
						publishButton = driver.find_element(By.XPATH, "//div[contains(@class,'_ab8w  _ab94 _ab99 _ab9f _ab9m _ab9p  _ab9- _abaa')]//button[contains(@type,'button')]").click()
						Logger.info("Post published")
						time.sleep(8)
					except Exception as e:
						Logger.warning(str(e))
						Logger.error("Could not add flight. Trying again.")
						driver.get("https://instagram.com")
						time.sleep(5)
						again += 1
					else:
						again = 99
					
				if (again == 10):
					Logger.error("Could not add report to Instagram.")
			
	if 'driver' in locals():
		driver.quit()


def main():
	global start_time, end_time
	start_time = time.time()
	config()
	check_config()

	if (test_mode):
		end_time = time.time()
		flights_info = {}
		with open("test_sample.json", "r", encoding="utf-8") as test_file:
			flights_info = json.load(test_file)

		co2_per_aircraft = dict(sorted(flights_info.items(), key=lambda it: it[1], reverse=True))
		report_path = generate(co2_per_aircraft)
		post_on_instagram(len(flights_info), report_path)
		send_log_by_mail(len(flights_info))
	else:
		flights_info = get_flights_info()
		Logger.info(flights_info[0])
		co2_per_aircraft = dict(sorted(flights_info[0].items(), key=lambda it: it[1], reverse=True))
		end_time = time.time()
		send_log_by_mail(flights_info[1])
		post_on_instagram(flights_info[1], report_path)

main()