# echo > /var/log/drbarak.pythonanywhere.com.error.log

import requests, time

import pandas as pd

from prog.chatbot_init import api_key, URL, icon_url
from prog.chatbot_init import df_CITIES_API, countries_df, MESSAGES
from prog.chatbot_init import cities_il_df, cities_il_df_set
from prog.chatbot_init import p, google_translate

def call_web(city_name, country_code, fahrenheit, one_call, LANG):
    state = ''
    api_url = f"{URL}q={city_name},{state},{country_code}&units={'metric' if not fahrenheit else 'imperial'}&lang={LANG}&appid={api_key}".format('weather')
    if one_call:
      cor = df_CITIES_API.loc[city_name].coord
      if type(cor) is not  dict: #more than one record for that city
        for index, row in df_CITIES_API.loc[city_name].iterrows():
          if row['coord'] != '' and (country_code == row['country'] or country_code == ''): # if no country code then use the first entry
            cor = row['coord']
            break
      api_url = f"{URL}lat={cor['lat']}&lon={cor['lon']}&exclude=minutely,hourly&units={'metric' if not fahrenheit else 'imperial'}&lang={LANG}&appid={api_key}".format('onecall')

    #p(api_url)

    response = requests.get(api_url)
    response_dict = response.json()

    weather = response_dict

    if response.status_code == 200:
        return weather
    elif response.status_code == 404:
        return None
    else:
        p(MESSAGES[LANG]["messages"]["web_error"].format(response.status_code, api_url))
        p(response_dict['message'])
        return None

def get_weather_info(actions, one_call, cnt, city_weather, default, LANG):
  all_action = actions[0][0] == 'all'  # always first
  #p(all_action)
  result = ''
  for action in actions:
    tag = action[0]
    if tag == "fahrenheit": continue
    user_act = action[1]
    if not one_call:
      data = city_weather if tag == "all" else city_weather['main'] \
        if tag in ["weatherTemp", "weatherPressure", 'temp', "pressure", "humidity"] else \
              city_weather['sys'] if tag == "sunrise" else city_weather['wind'] \
              if tag in ["weatherWind", "wind"] else city_weather[tag]
    else:
      data = city_weather
    #p('in loop', user_act, tag, data)
    if tag in ['clouds']:
      clouds_percentage = data['all'] if not one_call else data['clouds']
      if clouds_percentage < 10: # no clouds
        if 'clear sky' not in default.lower():
          result += f'{MESSAGES[LANG]["messages"]["clear sky"]}, '
        elif not all_action:
          result += f' {default},'
      elif default not in result:
        result += f' {default},'
      if all_action: continue
    if user_act == "rain":
      if user_act in default.lower():
        if default not in result:
          result += f' {default},'
      else:
        result += f' {MESSAGES[LANG]["messages"]["no"]} {user_act},'
      if all_action: continue
    if all_action and tag != 'all': continue
    if tag in ["weather", "weatherPressure","weatherWind","weatherTemp","all"]:
      if default not in result:
        result += f' {default},'
    if tag in ["weatherTemp", "weatherPressure", 'temp', "pressure", "humidity", "all"]:
      data_tag = data['main'] if tag == 'all' and not one_call else data
      '''
      p('in weather info 79', one_call, cnt, tag)
      p(data_tag)
      p(data)
      '''
      if tag in [ "weatherTemp", "temp", "all"]:
        for i, temp in enumerate(MESSAGES[LANG]["messages"]["temp"]):
          if i == 0:
            if cnt == 0:
              info = data_tag["temp"]
            else:
              info = data_tag["temp"]['day']
          elif i == 1:
            if cnt == 0:
              info = data_tag["feels_like"]
            else:
              info = data_tag["feels_like"]['day']
            if one_call and cnt == 0:
              break
          elif i == 2: info = data_tag["temp_min"] if cnt == 0 else data_tag["temp"]["min"]
          elif i == 3: info = data_tag["temp_max"] if cnt == 0 else data_tag["temp"]["max"]
          result += f' {temp} = {info},'
      if tag in ["weatherPressure", "pressure", "all"]:
        result += f' {MESSAGES[LANG]["messages"]["pressure"]} = {data_tag["pressure"]},'
      if tag in ["humidity", "all"]:
        result += f' {MESSAGES[LANG]["messages"]["humidity"]} = {data_tag["humidity"]},'
    if tag in ["wind", "weatherWind", "all"]:
      data_tag = data['wind'] if tag == 'all' and not one_call else data
      for i, wind in enumerate(MESSAGES[LANG]["messages"]["wind"]):
        if i == 0: info = data_tag["speed"] if not one_call else data_tag["wind_speed"]
        elif i == 1: info = data_tag["deg"] if not one_call else data_tag["wind_deg"]
        elif i == 2:
          if "gust" in data_tag:
            info = data_tag["gust"]
        elif "wind_gust" in data_tag:
            info = data_tag["wind_gust"]
        else:
            continue
        result += f' {wind} = {info},'
    if tag in ["visibility","all"]:
      if cnt > 0 and 'visibility' not in data:
        data_tag = MESSAGES[LANG]["messages"]["no_info"]
      else:
        data_tag = data['visibility'] if tag == 'all' or one_call else data
      result += f' {MESSAGES[LANG]["messages"]["visibility"]} = {data_tag},'
    if tag in ["sunrise","all"]:
      data_tag = data['sys'] if tag == 'all' and not one_call else data
      for i, wind in enumerate(MESSAGES[LANG]["messages"]["sunrise"]):
        if i == 0: info = data_tag["sunrise"]
        elif i == 1: info = data_tag["sunset"]
        result += f' {wind} = {time.strftime("%H:%M:%S", time.gmtime(info + 3 * 60 * 60))},'
  return result

def get_weather(days, location, actions, range_days, LANG):
  #p(dt, location)
  city_w = city = location[0][0]  # assume one city (not handling if there are 2 cities)
  country = location[0][1]
    # to avoid the error, when country has multiple values, 'The truth value of a Series is ambiguous. Use a.empty, a.bool(), a.item(), a.any() or a.all().'
  if type(country) == pd.Series:
    country = country.iloc[0]

  #p(city, city_w)
  result = ''

  #convert israeli cities to district that the API knows ('sharon' is in API because there is such city in Australia)
#  if country == 'israel' and city in cities_il_df_set: # cities_il_df.index.values: changed to SET() to improve speed (search in set is 100 times faster than in list()
  if country == 'israel' and city in cities_il_df_set:
        city_w = cities_il_df.loc[city].district
        if type(city_w) == pd.Series:
          city_w = city_w.iloc[0]

  #p(city_w, location)
  #p(country, len(countries_df.Name), country in list(countries_df.Name))
  if country in list(countries_df.Name):
    country_code = countries_df[countries_df.Name == country].index[0]
  else:
    country_code = ''
  #p(city_w, country_code)#

  fahrenheit = True if len([action for action in actions if action[0] == "fahrenheit"]) > 0 else False
  if days < 0: days = 0   # if asked for a date before today

  one_call = (days > 0 or range_days > 1)
  city_weather_resp = call_web(city_w, country_code, fahrenheit, one_call, LANG)

  if city_weather_resp is None:
    return MESSAGES[LANG]["messages"]["api_error"], ''
    # check what informtion the user asked for

  city_weather = city_weather_resp if not one_call else city_weather_resp["current"]

  default = city_weather["weather"][0]["description"]
  icon = city_weather["weather"][0]["icon"]
  url_icon = f"{icon_url}".format(icon)
  result = '' if days > 0 else MESSAGES[LANG]["messages"]["web_msg_current"]

  for cnt in range(days, 9):
    if cnt > 0:
      # bug in python - cannot have r += z + x if cond else y
      M = MESSAGES[LANG]["messages"]["web_days_msg"].format(cnt) if cnt > 1 else MESSAGES[LANG]["messages"]["web_day_msg"]
      result += '<br>' + M
      city_weather = city_weather_resp["daily"][cnt - 1]
    new_result = get_weather_info(actions, one_call, cnt, city_weather, default, LANG)
    #cnt, new_result)
    result += new_result
    if not one_call: break
    if cnt > 0:
      range_days -= 1
      if range_days == 0: break

  if result == '': result = default
  if result[-1] == ',': result = result[:-1]
  country = location[0][1]
  if type(country) == pd.Series:
    country = country.iloc[0]
  if LANG != 'en': # in case there are parts of the answer which are not in the proper langauge
    city = google_translate(city, dest=LANG, VERBOSE=True)
    '''
    response = translator.translate(city, dest=LANG) # need to separet city from country in case one of them has multi words and google doe not keep the qoutation mark as needed
    #response = translator.translate(f"({city}, {country})", dest=LANG)
    #city, country = response.text
    p(f"{response.origin} ({response.src}) --> {response.text} ({response.dest})")
    city = response.text
    response = translator.translate(country, dest=LANG)
    country = response.text
    '''
    country = google_translate(country, dest=LANG, VERBOSE=True)
  response =  MESSAGES[LANG]["messages"]["web_msg"].format(city.capitalize(), country.capitalize()) + result
  return response, url_icon
