from django.shortcuts import render, redirect
from darksky import forecast
from datetime import date,timedelta,datetime
from bs4 import BeautifulSoup
from ipstack import GeoLookup
import requests
import json
from fake_useragent import UserAgent
import pandas as pd
from .models import City
from .forms import CityForm
#from urllib3 import urlopen


# Create your views here.
def home(request):

    geo_lookup = GeoLookup("458015c5b9b623034642993da2d3e712") #taking api from ipstack to detect location automatically
    location = geo_lookup.get_own_location()
    print(location) # we are not getting bangalore as location from this api, it is showing nelamangala, therefore we will be hardcoding the location

    lat = location['latitude']
    lng = location['longitude']
    region = location['region_name']

    city = 12.9716, 77.5937 #longitude and latitude of bengaluru according to google
    #city = lat,lng


    weekday = date.today()

    weekly_weather = {}
    hourly_weather = {}

    # 84ed95947b8889a445be094030dc2af3 - secret key from darksky to use their weather api

    with forecast('84ed95947b8889a445be094030dc2af3',*city) as city:
        for day in city.daily:
            tMin = (day.temperatureMin - 32) * 5/9 #this will convert fahrenheit to celsius, °C = (°F - 32) x 5/9
            tMax = (day.temperatureMax - 32) * 5/9 #this will convert fahrenheit to celsius, °C = (°F - 32) x 5/9
            day = dict(day = date.strftime(weekday,'%A'), sum = day.summary, tempMin = round(tMin), tempMax = round(tMax),)
            print('{day} --- {sum} -- {tempMin} - {tempMax}'.format(**day)) #this will get weather forecast on webserver, this is just to check
            weekday += timedelta(days=1)

            pic = ''
            summary = ('{sum}'.format(**day).lower())

            if 'drizzle' in summary:    #this will loop through and get the png's for the weather accordingly.
                pic = 'light-rain.png'  #the url is present on home.html, key and value will be taken from here.
            elif 'rain' in summary:
                pic = 'rain.png'
            elif 'clear' in summary:
                pic = 'sun.png'
            elif 'partly cloudy' in summary:
                pic = 'partly-cloudy-day.png'
            else:
                pic = 'clouds.png'

            weekly_weather.update({'{day}'.format(**day):{'tempMin':'{tempMin}'.format(**day),'tempMax':'{tempMax}'.format(**day),'pic':pic}})
            #weekly_weather as the name suggest will get the weekly weather update.

    today = weekly_weather[(date.today().strftime("%A"))]
    del weekly_weather[(date.today().strftime("%A"))]  #in the weekly weather we do not want to know todays weather, therefore deleting this.

    hour = datetime.now().hour
    location  = forecast('84ed95947b8889a445be094030dc2af3', 12.9716, 77.5937,)
    i = 0

    hour_ = ''

    while hour < 24: # this will get the hourly data

        temp1 = (location.hourly[i].temperature - 32) * 5/9

        temp = round(temp1)
        #print(temp)

        pic = ''
        summary = location.hourly[i].summary.lower()

        if 'drizzle' in summary:    #this will loop through and get the png's for the weather accordingly.
            pic = 'light-rain.png'  #the url is present on home.html, key and value will be taken from here.
        elif 'rain' in summary:
            pic = 'rain.png'
        elif 'clear' in summary:
            pic = 'sun.png'
        elif 'partly cloudy' in summary:
            pic = 'partly-cloudy-day.png'
        else:
            pic = 'clouds.png'

        if hour < 12:
            hour_ = '{}'.format(hour)
            hourly_weather.update({hour_:{'pic':pic,'temp':temp}})
            #print('{}am - {}'.format(hour,temp))
        else:
            hour_ = '{}'.format(hour)
            hourly_weather.update({hour_:{'pic':pic,'temp':temp}})
            #print('{}pm - {}'.format(hour,temp))

        hour+=1
        i+=1


    return render(request,'home.html',{'weekly_weather':weekly_weather,'hourly_weather':hourly_weather,'today':today,})

def weather(request):
    url = 'http://api.openweathermap.org/data/2.5/weather?q={}&units=metric&APPID=85db121006fe82a6039f53fb82500bbe'

    err_msg = ''
    message = ''
    message_class = ''

    if request.method == 'POST': #this will allow user to add cities to the page to check the weather
        form = CityForm(request.POST)

        if form.is_valid():
            new_city = form.cleaned_data['name']                             #new_city = the city user adds on the page
            existing_city_count = City.objects.filter(name=new_city).count() #checking for duplicate entries
            if existing_city_count == 0:                                     #add city if it isn't already present in the db
                r = requests.get(url.format(new_city)).json()
                #qprint(r)
                if r['cod'] == 200:   # when city exists, cod is 200, therefore we'll save it, enable the print statement                                         # above to check, when the city does not exist the error message is cod = 404
                    form.save()
                else:
                    err_msg = 'City does not exist'
            else:
                err_msg = 'City already exists on this page'

        if err_msg:
            message = err_msg
            message_class = 'is-danger'  #this will throw an error if city doesn't exist
        else:
            message = 'City added successfully'
            message_class = 'is-success'       #this will throw a success message once the city has been added


    form = CityForm()

    cities = City.objects.all()

    weather_data = []

    for city in cities:
        r = requests.get(url.format(city)).json()  #using api to get a json of the page
        print(r)
        city_weather = {
            'city' : city.name,
            'temperature_min' : r['main']['temp_min'],
            'temperature_max' : r['main']['temp_max'],
            'humidity' : r['main']['humidity'],
            'description' : r['weather'][0]['description'],
            'icon' : r['weather'][0]['icon'],
        }

        weather_data.append(city_weather)

    print(weather_data)

    context = {'weather_data' : weather_data,
               'form' : form,
               'message' : message,
               'message_class' : message_class,
              }
    return render(request, 'weather.html', context)

def delete_city(request, city_name): #this is to delete a city from the list of cities created from the above function
    City.objects.get(name=city_name).delete()
    return redirect('weather')


def airquality(request):

    city = 'Bengaluru'

    #this script scraps details from - http://aqicn.org/city/india/bengaluru/hebbal/

    user_agent = UserAgent()

    url1 = 'http://aqicn.org/city/india/bengaluru/hebbal/'
    url2 = 'http://aqicn.org/city/india/bengaluru/silk-board/'
    url3 = 'http://aqicn.org/city/india/bangalore/city-railway-station/'

    url = [url1, url2, url3]

    print(url)
    pages = []
    status = []
    aqi = []
    place = []

    #print(len(url))

    for item in url: #This will create a soup of the pages
        page = requests.get(item,headers={'user-agent':user_agent.chrome})
        soup = BeautifulSoup(page.text, 'lxml')

        #print(soup)

        for t in soup.find_all('div', class_={'aqivalue'}):
            s = t['title']
            status.append(s)

        for z in soup.find_all('div', class_={'aqivalue'}): # this will show values of all towns within bangalore
            aq = z.string
            aqi.append(aq)

        for p in soup.find_all('div', class_={'aqiwgt-table-title'}): # this will show values of all towns within bangalore
            pl = p.a['title']
            place.append(pl)

    data = {'Status': status,'AQI':aqi, 'Place':place}

    print(data)

    #print(data['Place'][0])
    #print(data['Status'][0])
    #print(data['AQI'][0])

    #print(data['Place'][1])
    #print(data['Status'][10])
    #print(data['AQI'][10])

    #print(data['Place'][2])
    #print(data['Status'][1])
    #print(data['AQI'][1])

    city1 = data['Place'][0]
    print(city1)
    quality1 = data['AQI'][0]
    status1 = data['Status'][0]

    print(data['Place'][1])
    print(data['Status'][10])
    print(data['AQI'][10])

    city2 = data['Place'][1]
    print(city2)
    quality2 = data['AQI'][10]
    status2 = data['Status'][10]

    city3 = data['Place'][2]
    print(city3)
    quality3 = data['AQI'][1]
    status3 = data['Status'][1]

    air_quality1 = {
        'city' : city1,
        'air_quality' : quality1,
        'status' : status1,
    }

    air_quality2 = {
        'city' : city2,
        'air_quality' : quality2,
        'status' : status2,
    }

    air_quality3 = {
        'city' : city3,
        'air_quality' : quality3,
        'status' : status3,
    }

    #print(air_quality)

    context = {'air_quality1': air_quality1, 'air_quality2': air_quality2, 'air_quality3': air_quality3,}

    return render(request, 'airquality.html', context)

def about(request):
    return render(request, 'about.html',)
