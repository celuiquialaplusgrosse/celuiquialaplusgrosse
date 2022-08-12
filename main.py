#!/usr/bin/python3
from cgi import print_arguments
import os
import sys
import re
import random
import requests
import time
import datetime
import locale
import csv
import json
import folium
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
import geopy.distance
import smtplib, ssl

def read_config():
	config_file = 'config.json'

	global log_file, aircrafts, instagram_info, mail_info, start_days_ago, end_days_ago, gecko_driver_path, firefox_profile_path, hashtags, api_url

	with open(f'./{config_file}', 'r+') as f:
		config = json.load(f)
		log_file = config["log_file"]
		aircrafts = config["aircrafts"]
		instagram_info = config["instagram"]
		mail_info = config["mail"]
		start_days_ago = config["start_days_ago"]
		end_days_ago = config["end_days_ago"]
		gecko_driver_path = config["gecko_driver_path"]
		firefox_profile_path = config["firefox_profile_path"]
		hashtags = config["hashtags"]
		api_url = config["api_url"]

		# for i in range(0, 35):
		# 	data[f"{i}"] = f"tile-{i}.png"

		# json.dump(data, f)

def print_warning(message):
	print("\033[1;33m[WARNING]\033[1;37m " + message)

def print_error(message):
	print("\033[1;31m[ERROR]\033[1;37m " + message)

def check_config():
	for aircraft in aircrafts:
		if aircraft["ton_per_km"] == "":
			print_warning(f"""No evaluation for aircraft {aircraft["registry"]} owned/operated by {aircraft["owner_or_operator"]}""")

	if len(hashtags) == 0:
		print_warning("No hashtags will be added to the Instagram post.")

	if instagram_info["username"] == "" or instagram_info["password"] == "":
		print_error("Incomplete info for Instagram connection.")
		sys.exit()

	if mail_info["smtp_addr"] == "" or mail["smtp_port"] == "" or mail["email"] == "" or mail["password"] == "":
		print_error("Incomplete info for email.")
		sys.exit()

	if start_days_ago == "":
		print_error("No value for 'start_days_ago'.")
		sys.exit()

	if end_days_ago == "":
		print_error("No value for 'end_days_ago'.")
		sys.exit()

	if gecko_driver_path == "":
		print_error("No value for 'gecko_driver_path'.")
		sys.exit()
	elif not os.path.isdir(gecko_driver_path):
		print_error("Wrong path for 'gecko_driver_path'.")
		sys.exit()

	if firefox_profile_path == "":
		print_error("No value for 'firefox_profile_path'.")
		sys.exit()
	elif not os.path.isdir(firefox_profile_path):
		print_error("Wrong path for 'firefox_profile_path'.")
		sys.exit()



#########################################################################################
# Script params
#script_path = '/absolute/path/to/script/' # the '/' at the end is needed
script_path = os.path.realpath(__file__)
ask = False # ask before running
openskynetwork = True # check flights on openskynetwork (alternative: own json)
instagram = False # upload to instagram
send_email = True # send recap email
headless_instagram = True  # hide Instagram browsing
log_file = True # write console output to log file


# Browser params
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
options = Options() # first instance of browser -> Instagram
options.add_argument("-profile")
options.add_argument(r'/path/to/firefox/profile/.mozilla/firefox/regatzrxsd.default') # use a profile to avoid logging in to Instagram each time
if headless_instagram: options.add_argument("--headless")
options2 = Options() # second instance of browser -> creates maps

# Instagram
instagram_post = "{day} | {departure} -> {arrival} | {duration} | ~ {co2} t CO2\n.\n{hashtags}\n.\nLes émissions de CO2 sont des estimations.\nLa trajectoire de vol représentée est illustrative."

# Others
locale.setlocale(locale.LC_TIME,'') # For French date format
		
# Write in log or print in console
if log_file: 
	sys.stdout = open(log_file, 'w')
else: 
	open(log_file, 'w').close()

start_time = time.time()

# Open Sky API request
begin = int(start_time - start_days_ago*24*60*60)
end = int(start_time - end_days_ago*24*60*60)

flights_list = {}
nb_flights_new = 0

co2_per_aircraft = {}

for aircraft in aircrafts:
	requestURL = api_url + '?icao24=' + aircraft["icao24"] + '&begin=' + str(begin) + '&end=' + str(end) 

	# Requesting API
	for i in range(20):
		try:
			print('Requesting OpenSky Network API')
			print(requestURL)
			r = requests.get(requestURL, headers=headers,timeout=10)
		except:
			print('Cannot access OpenSky Network API, sleep for 1min')
			r = None
			time.sleep(60)
		else:
			break

	if r is None :
		print('Cannot reach OpenSky API - just re-run the script')
		flights = []
	else:
		flights = r.json()
		
	nb_flights_found = len(flights)

	flights_list[aircraft["icao24"]] = []

	# Getting flights
	for flight in flights:
		if (flight['estDepartureAirport'] is None or flight['estArrivalAirport'] is None or flight['firstSeen'] is None or flight['estDepartureAirport'] == flight['estArrivalAirport']):
			continue
		# Getting airport municipalities and day of travel
		with open("airports.csv") as f:
			airports = csv.DictReader(f)
			for airport in airports:
				if(airport['ident'] == flight['estDepartureAirport']):
					departure = airport['municipality']
					departure_coord = [airport['latitude_deg'],airport['longitude_deg']]
				if(airport['ident'] == flight['estArrivalAirport']):
					arrival = airport['municipality']
					arrival_coord = [airport['latitude_deg'],airport['longitude_deg']]
		departure_time = str(datetime.date.fromtimestamp(flight['firstSeen']).strftime("%d.%m.%Y"))
		duration = flight['lastSeen'] - flight['firstSeen']
		# Removing flights already fetched
		with open("flights.csv", "r") as f:
			oldFlights = csv.DictReader(f)
			old = False
			for oldFlight in oldFlights:
				if (oldFlight['departure'] == departure and oldFlight['arrival'] == arrival and oldFlight['day'] == departure_time):
					old = True
					break
			if not old:
				distance = geopy.distance.geodesic(departure_coord, arrival_coord).km
				co2 = round(distance * aircraft["tom_per_km"], 1)
				#flights_list[aircraft["icao24"]].insert(0, [departure, arrival, departure_time, departure_coord, arrival_coord, co2, duration])
				co2_per_aircraft[aircraft["icao24"]] += co2

	# Print flight list
	#for (index,flight) in enumerate(flights_list[aircraft["icao24"]]): print(str(index) + " | " + flight[0] + " -> " + flight[1] + " | " + flight[2])

	nb_flights_new += len(flights_list[aircraft["icao24"]])
	nb_flights_uploaded = 0


# if nb_flights_new != 0:
# 	if instagram:
# 		# Go to Instagram
# 		print("Go to Instagram")
# 		driver = webdriver.Firefox(service=Service(gecko_driver_path), options=options)
# 		driver.get('https://instagram.com')
# 		time.sleep(5)
		
# 		# Log in only if sessionId did not work (looking for publish button)
# 		try:
# 			driver.find_element(By.XPATH, '//*[@class="_abl- _abm2"]')
# 		except:
# 			again = 0
# 			while (again < 10):
# 				print("Not logged, get instagram")
# 				if (re.search("Allow the use of cookies", driver.page_source) or re.search("utilisation des cookies", driver.page_source)):
# 					allowCookiesButton = driver.find_element(By.XPATH, '//*[@class="aOOlW  bIiDR  "]').click()
# 					time.sleep(5)
# 					print("Closed cookie pop-up")
# 				usernameInput = driver.find_element(By.XPATH, '//*[@name="username"]').send_keys(instagram_info["username"])
# 				passwordInput = driver.find_element(By.XPATH, '//*[@name="password"]').send_keys(instagram_info["password"])
# 				loginButton = driver.find_element(By.XPATH, '//*[@type="submit"]').click()
# 				print("Sent login details")
# 				time.sleep(5)
# 				if (re.search("Forgot password", driver.page_source)):
# 					print('Cannot log in, sleep for 2min')
# 					time.sleep(120)
# 					driver.get('https://google.com') #reload by changing page
# 					driver.get('https://instagram.com')
# 					again += 1
# 				else:
# 					again = 99
# 					print("Logged in Instagram")
# 		else:	
# 			again = 99
# 			print("Logged in Instagram")
# 			if (re.search("Not Now", driver.page_source) or re.search("Plus tard", driver.page_source)):
# 				notNowCookieButton = driver.find_element(By.XPATH, '//*[@class="aOOlW   HoLwm "]').click()
# 	else:
# 		again = 99

# 	if (again == 10):
# 		print("Could not log into Instagram - just re-run script later")
# 	else:
# 		i = 0
# 		for flight in flightList:
# 			# gather flight infos
# 			departure = flight[0]
# 			arrival = flight[1]
# 			day = flight[2]
# 			departure_coord = flight[3]
# 			arrival_coord = flight[4]
# 			co2 = str(flight[5])
# 			duration = time.strftime("%-Hh%Mmin", time.gmtime(flight[6]))
# 			print("[Flight " + str(i) + " - " + departure + " -> " + arrival + "]")

# 			# convert GPS coordinates to numbers
# 			departure_coord[0] = float(departure_coord[0])
# 			departure_coord[1] = float(departure_coord[1])
# 			arrival_coord[0] = float(arrival_coord[0])
# 			arrival_coord[1] = float(arrival_coord[1])
			
# 			# Turn the globe to keep distance < 180°
# 			if abs(arrival_coord[1]-departure_coord[1])>180:
# 				if (arrival_coord[1] < departure_coord[1]):
# 					departure_coord[1] -= 360
# 				else:
# 					arrival_coord[1] -= 360
				
# 			# Create the map
# 			map = folium.Map(zoom_control=False)
# 			map.fit_bounds([departure_coord, arrival_coord], padding=[120,120]);

# 			# Add plane and city names
# 			if (departure_coord[1] < arrival_coord[1]): # position the plane towards arrival
# 				planeSide = "toright"
# 			else: 
# 				planeSide = "toleft"

# 			if (departure_coord[0] < arrival_coord[0]): # write arrival city name above or below coordinate (not to cross plane path)
# 				cityMarginTop = "-50"
# 			else:
# 				cityMarginTop = "10"
			
# 			# Add cities and plane
# 			folium.Marker(
# 					departure_coord,
# 					icon=folium.DivIcon(html=f"""<div style='transform: scale(0.45) translate(-90px, -210px)'><img src="icons/plane""" + planeSide + """.png"></div>""")
# 				 ).add_to(map)
# 			folium.CircleMarker(
# 					arrival_coord,
# 					color="black",
# 					fill_color='black', 
# 					radius=3
# 					).add_to(map)
			
# 			folium.Marker(
# 					departure_coord,
# 					icon=folium.DivIcon(html=f"""<div style='font-family: Arial; margin-top: 40px; font-size: 3.1em; font-weight: 600; color:black; width: max-content; transform: translate(-50%)'>""" + flight[0] + """</div>""")
# 				 ).add_to(map)
# 			folium.Marker(
# 					arrival_coord,
# 					icon=folium.DivIcon(html=f"""<div style='font-family: Arial; margin-top: """ + cityMarginTop + """px; font-size: 3.1em; font-weight: 600; color: black; width: max-content; transform: translate(-50%);'>""" + flight[1] + """</div>""")
# 				 ).add_to(map)

# 			# Add curve between airports
# 			curve = []
# 			slope = abs(arrival_coord[1]-departure_coord[1])/500
# 			for t in range(101):
# 				curve.append([
# 					departure_coord[0] + slope*t + (arrival_coord[0]-departure_coord[0]-slope*100)/10000*t*t,
# 					departure_coord[1] + t*(arrival_coord[1]-departure_coord[1])/100
# 					])

# 			folium.PolyLine(
# 				curve,
# 				weight=3,
# 				color='black'
# 				).add_to(map)

# 			# Export the map to HTML
# 			print("Creating map")
# 			outputFile = "map.html"
# 			map.save(outputFile)
# 			mapURL = 'file://{0}/{1}'.format(os.getcwd(), outputFile)

# 			# Add 'absolute position' content to HTML
# 			# Folium does not allow for it, so use a direct solution
# 			with open(outputFile, 'a') as mapHTML:
# 				mapHTML.write(
# 				"""
# 				<div style='position: absolute; z-index: 9999; font-family: Arial; font-size: 2.4em; padding-top:5px; font-weight: 600; color: black; left: 20px; top: 20px;'>""" 
# 				+ aircraftName +
# 				"""</div>
# 				<div style='position: absolute; z-index: 9999; font-family: Arial; font-size: 2.7em; font-weight: 600; color: black; right: 20px; top: 20px;'>"""
# 				+ day +
# 				"""
# 				</div>
# 				<div style='position: absolute; z-index: 9999; font-family: Arial; font-size: 2.7em; font-weight: 600; color: black; left: 20px; bottom: 20px;'>"""
# 				+ duration +
# 				"""</div>
# 				<div style='position: absolute; z-index: 9999; font-family: Arial; font-size: 2.7em; font-weight: 600; color: black; right: 20px; bottom: 20px;'>~ """
# 				+ co2 +
# 				""" t CO2</div>""")
			
# 			# Open it with webdriver
# 			driver2 = webdriver.Firefox(service=Service(gecko_driver_path), options=options2)
# 			driver2.set_window_size(1080, 1165)

# 			# Save screenshot (png)
# 			driver2.get(mapURL)
# 			time.sleep(6)
# 			output = 'output/output'+str(i)+'.png'
# 			print("Taking screenshot")
# 			driver2.save_screenshot(output)
# 			driver2.quit()
			
# 			# Convert to jpg
# 			im = Image.open(output)
# 			output = 'output/output'+str(i)+'.jpg'
# 			rgb_im = im.convert('RGB')
# 			rgb_im.save(output)

# 			time.sleep(5)
			
# 			# Add flight to Instagram
# 			if instagram:
# 				again = 0
# 				while (again < 10):
# 					#Randomly choose hashtags
# 					sample = random.sample(range(0, len(hashtags)), nbHashtags)
# 					hashtagSample = ""
# 					for i in sample:
# 						hashtagSample += "#" + hashtags[i] + " "

# 					# Publish image
# 					try:
# 						print("Adding map to Instagram")
# 						newPostButton = driver.find_element(By.XPATH, '//*[@aria-label="Nouvelle publication"]').click()
						
# 						print("New post window opened")
# 						time.sleep(5)
# 						dropZone = driver.find_element(By.XPATH, "//div[contains(@class,'_ac2r')]//input[contains(@type,'file')]").send_keys(script_path + output)
# 						print("Map dropped in drop zone")
# 						time.sleep(8)
# 						submitButton = driver.find_element(By.XPATH, "//div[contains(@class,'_ab8w  _ab94 _ab99 _ab9f _ab9m _ab9p  _ab9- _abaa')]//button[contains(@type,'button')]").click()
# 						print("Map submitted")
# 						time.sleep(8)
# 						noFilterButton = driver.find_element(By.XPATH, "//div[contains(@class,'_ab8w  _ab94 _ab99 _ab9f _ab9m _ab9p  _ab9- _abaa')]//button[contains(@type,'button')]").click()
# 						print("Next no filter clicked")
# 						time.sleep(5)
							
# 						captionArea = driver.find_element(By.XPATH, '//*[@class="_ablz _aaeg"]')
# 						captionArea.send_keys(instagram_post.format(day=day,departure=departure,arrival=arrival,duration=duration,co2=co2, hashtags=hashtagSample))
						
# 						# Test mode prevent from posting
# 						if (test):
# 							post = input("Post flight? (y/n)")
# 							if (post != "y"):
# 								quit()
						
# 						print("Caption sent")						
# 						publishButton = driver.find_element(By.XPATH, "//div[contains(@class,'_ab8w  _ab94 _ab99 _ab9f _ab9m _ab9p  _ab9- _abaa')]//button[contains(@type,'button')]").click()
# 						print("Post published")
# 						time.sleep(8)
# 						confirmPopUpCloseButton = driver.find_element(By.XPATH, '//*[@class="fg7vo5n6 lrzqjn8y"]').click()
# 						time.sleep(5)

# 						# Record flight into .csv file
# 						with open("flights.csv", "a") as f:
# 							oldFlightsWriter = csv.writer(f)
# 							oldFlightsWriter.writerow(flight)
# 					except:
# 						print("Could not add flight. Trying again.")
# 						driver.get('https://instagram.com')
# 						time.sleep(5)
# 						again += 1
# 					else:
# 						again = 99
# 						nb_flights_uploaded += 1
					
# 				if (again == 10):
# 					print('Could not add flight to Instagram. Ignore the flight : ' + day + ' | ' + departure + ' -> ' + arrival)
			
# 			i+=1

# if 'driver' in locals():
# 	driver.quit()

end_time = time.time()

# # print general results
# print("API : " + str(nbFlightsFoundAPI))
# print("New : " + str(nb_flights_new))
# print("Uploaded : " + str(nb_flights_uploaded))

print(co2_per_aircraft)

# stop logging and send logs via email
sys.stdout.close()
with open(log_file, "r") as f:
	log = f.read()

message = """\
Subject: Avion

""" + str(nb_flights_uploaded) + """/""" + str(nb_flights_new) + """ nouveaux vols


Debut: """ + str(datetime.datetime.fromtimestamp(start_time).strftime("%H.%M:%S")) + """
Fin: """ + str(datetime.datetime.fromtimestamp(end_time).strftime("%H.%M:%S")) + """


Log:

""" + log

if send_email:
	# Create a secure SSL context
	context = ssl.create_default_context()
	# Send email
	with smtplib.SMTP_SSL(mail_info["smtp_addr"], mail_info["smtp_port"], context=context) as server:
		server.login(mail_info["email"], mail_info["password"])
		server.sendmail(mail_info["email"], mail_info["email"], message)

