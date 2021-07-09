# echo > /var/log/drbarak.pythonanywhere.com.error.log

from flask import render_template, redirect, request
from flask_app import session

from prog.forms import ChatForm

import spacy, random, requests, bs4, time, json
from spacy.matcher import PhraseMatcher

from dateutil.parser import parse
from datetime import datetime
from wordtodigits import convert

import pandas as pd

from prog.chatbot_init import nlp, stopwords, remove_punct_dict, space_punct_dict, api_key, URL, path, icon_url
from prog.chatbot_init import df_CITIES_API, CITIES_API_country_code
from prog.chatbot_init import largest_df, countries_df
from prog.chatbot_init import cities_il_df, QUESTIONS
from prog.chatbot_init import capitals_df, CAPITALS
from prog.chatbot_init import ACTIONS#, ACTIONS_patterns, ACTIONS_tags
from prog.chatbot_init import MESSAGES_lang, MESSAGES, MESSAGES_en, intents, intents_en
from prog.chatbot_init import p, send_email, googletrans_api, translator
from prog.chatbot_init import dayInWeek, dateToNum, listNlp, tz, NO_DAYS, datesDf

IDLE_TIME = 60 * 30 # max half an hour between questions to the bot

def chatbot():
    if 'chat_' not in session:
        p()
        p('------------------------------')
        p(f"Start ChatBot, {spacy.__version__}, user_ip={request.headers['X-Real-IP']}")
        session['chat_'] = 'chat_'
        session['username_'] = 'admin_'
        session['df_chat'] = []
        session['time'] = time.time()
        session['google'] = False
        session['index'] = 1
        session['clear'] = False
        session['debug'] = 0
        session['lang'] = 'en'
        session['new_lang'] = ''
        session['user_msg'] = ''
        session['error'] = ''
        session['RUN_TEST'] = 0
        session['switched_lang'] = False
        session['url_icon'] = ''
        session['YES_NO'] = False
        session['yes_addition'] = ''

        p(request.headers['X-Real-IP'], request.headers['X-Forwarded-For'])
        if request.headers['X-Real-IP'] not in ['82.81.245.207', '50.17.220.95'] : # dr barak ip - no need to get a notice each time I log in
            #p(request.headers['X-Real-IP'] != '82.81.245.207', request.headers['X-Real-IP'], type(request.headers['X-Real-IP']))
            send_email(ip = request.headers['X-Real-IP'])
    else:
        if 'google' not in session:
            session['google'] = False
        if 'clear' not in session:
            session['clear'] = False
        if not 'lang' in session:
            session['lang'] = 'en'
        if not 'debug' in session:
            session['debug'] = 0
        if not 'new_lang' in session:
            session['new_lang'] = ''
        if not 'user_msg' in session:
            session['user_msg'] = ''
        if not 'error' in session:
            session['error'] = ''
        if not 'RUN_TEST' in session:
            session['RUN_TEST'] = 0
        if not 'switched_lang' in session:
            session['switched_lang'] = False
        if not 'url_icon' in session:
            session['url_icon'] = ''
        if not 'YES_NO' in session:
            session['YES_NO'] = False
            session['yes_addition'] = ''

        if 'time' in session:
            session_time = session['time']
            delta = time.time() - session_time
            if delta > IDLE_TIME or session['index'] == 0:
                session['df_chat'] = []
                session['time'] = time.time()
                session['index'] = 1
                session['google'] = False
                session['clear'] = False
                session['RUN_TEST'] = 0
                session['switched_lang'] = False
                session['url_icon'] = ''
                session['YES_NO'] = False
                session['yes_addition'] = ''

            else:  # reset the session time as long as no delay of more than idle_time
                session['time'] = time.time()
        else:
            session['df_chat'] = []
            session['time'] = time.time()
            session['google'] = False
            session['index'] = 1
            session['clear'] = False
            session['RUN_TEST'] = 0
            session['switched_lang'] = False
            session['url_icon'] = ''
            session['YES_NO'] = False
            session['yes_addition'] = ''

    LANG = session['lang']
    new_lang = session['new_lang']
    user_msg = session['user_msg']
    if session['df_chat'] == [] or len(session['df_chat']) == 0:
        session['url_icon'] = ''

    id = intents[LANG]["messages"][5]["responses"][6]
    conv = intents[LANG]["messages"][5]["responses"][7]
    df_chat = pd.DataFrame(session['df_chat'], columns=['index', id, conv])
    form = ChatForm()
    if request.method == 'POST':
        #p('debug', session['debug'], form.google.data, form.debug.data)
        if form.run_bot.data or form.run_test.data or form.send_log.data:
            if form.run_test.data:
                if session['RUN_TEST'] == 0: session['RUN_TEST'] = 1
            else:
                session['RUN_TEST'] = 0
                if form.send_log.data:
                    form.user_msg.data = 'send log to drbarak@talkie.co.il'
            answer, goodbye = run_bot(form.user_msg.data, session['debug'], LANG, new_lang, user_msg)
            if session['clear']:
                session['index'] = 1
                session['df_chat'] = []
                session['clear'] = False
                session['url_icon'] = ''
            index = session['index']
            id = intents[LANG]["messages"][5]["responses"][6]
            conv = intents[LANG]["messages"][5]["responses"][7]
            bot = intents[LANG]["messages"][5]["responses"][5]
            you = intents[LANG]["messages"][5]["responses"][4]
            session['df_chat'] = [[index + 1, bot + ': ', answer], [index, you + ': ', session['user_msg']]] + session['df_chat']
            df_chat = pd.DataFrame(session['df_chat'], columns=['index', id, conv])
            session['index'] = index + 2
            if goodbye == True:
                session['clear'] = True # clear the log after displaying this message
            return redirect('/chatbot')  # to clear the form fields

        elif form.google.data:
            session['google'] = False if session['google'] else True
            #send_email('Google was clicked')
        elif form.debug.data:
            session['debug'] = 0 if session['debug'] > 0 else 2
    #df_chat_html = df_chat.style.applymap(lambda attr: 'font-weight: bold;', subset=['index'])
    df_chat_html = (df_chat.style
                        .set_properties(subset=['index'], **{'font-weight': 'bold'})
                        .set_properties(subset=[conv], **{'width': '500px'})
                        .set_properties(subset=['index'], **{'width': '20px'})
                        .hide_index()
                        .render()
                        .replace('index','')
                        )
    form.run_bot.label.text = intents[LANG]["messages"][5]["responses"][1]
    html = render_template('chatbot.html', title='CHAT BOT', form=form, error=session['error'],
                        df_chat=df_chat_html, length=len(df_chat), debug=session['debug'],
                        google=session['google'], prompts=intents[LANG]["messages"][5]["responses"],
                        lang=LANG, run_test=session['RUN_TEST'], url_icon=session['url_icon'])
    rtl = 'rtl' if LANG in ['he', 'iw', 'ar'] else ''
    return html.replace('<html',f'<html dir="{rtl}" lang="{LANG}"')

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
      #one_call, tag, data_tag, data)
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
            if one_call  and cnt == 0:
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
  #p(city, city_w)
  result = ''

  #convert israeli cities to district that the API knows ('sharon' is in API because there is such city in Australia)
  if country == 'israel' and city in cities_il_df.index.values:
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

"""# Get Parts (POS)"""

TODAY = 0

def is_valid_date(dt, disp=False):
  if dt:
    try:
      dt_now = datetime.now(tz)
      if len(dt) == 4 or len(dt) == 3: # add year
        dt = f'{dt_now.year}{dt}'
      dt = dt.translate(space_punct_dict)
      new_date = str(parse(dt, fuzzy=True))[:10]
      year = int(new_date[:4])
      month = int(new_date[5:7])
      day = int(new_date[8:])
      dt1 = tz.localize(datetime(dt_now.year, dt_now.month, dt_now.day))
      dt2 = tz.localize(datetime(year, month, day))
      ndays = (dt2 - dt1).days
      return True, year, month, day, ndays
    except Exception as e:
      p(e)
      if disp: p('invalid:', dt)
      return False, None, None, None, None
  return False

def get_todayDayWeek():
  #to day of the week such that sunday=1,.. saturday=7 from monday=0...sat=5, sunday=6
  todayDate = datetime.now(tz)
  #todayDayWeek=(todayDate.weekday()+2-7) if (todayDate.weekday()+2>7) else  (todayDate.weekday()+2) # get day of week today
  todayDayWeek = 1 if todayDate.weekday() == 6 else todayDate.weekday() + 2
  return todayDayWeek

def get_delta_days_weekday(text, dayInText_org=-NO_DAYS, weekend = False, range_days = 0, disp=False):
  if disp: p('get_delta_days_weekday', dayInText_org)
  days, week, dayInText = NO_DAYS, -1, dayInText_org
  if TODAY == 0:
    #todayDate = datetime.now(tz)
    #todayDayWeek=(todayDate.weekday()+2-7) if (todayDate.weekday()+2>7) else  (todayDate.weekday()+2) # get day of week today
    #todayDayWeek = 1 if todayDate.weekday() == 6 else todayDate.weekday() + 2 # from day of the week such that sunday=1,.. saturday=7 from monday=0...sat=5, sunday=6
    todayDayWeek = get_todayDayWeek()
  else:
    todayDayWeek = TODAY
  if disp: p('todayDayWeek', todayDayWeek, TODAY, text, text in dayInWeek)#, todayDate.weekday())

  if text in dayInWeek: # if there is only one word of day in week
    if dayInText_org == -NO_DAYS: # if we did not find a day already
      dayInText = dayInWeek[text]
      if disp: p(text, dayInText, dayInWeek)
      if todayDayWeek <= dayInText:
        days = dayInText - todayDayWeek
      else:
        days = dayInText - todayDayWeek + 7
    if disp: p('days = ', days)
  else:# if there are additional word like 'next sunday'
    doc = nlp(text)
    for entity in doc:
      if disp: print(f'entity = {entity.text}, lemma_ = {entity.lemma_}')
      if entity.text in dayInWeek:
        dayInText = dayInWeek[entity.text.lower()]
        if todayDayWeek <= dayInText:
          days = dayInText - todayDayWeek
        else:
          days = dayInText - todayDayWeek + 7
          week = 0
      elif entity.lemma_ == 'next' and week == -1:
        if disp: print('get next')
        week = 1
      elif entity.lemma_ == 'weekend' and not weekend and week == -1:
        if disp: p("is Weekend2", entity.lemma_)
        week = 1
        range_days = 2
        weekend = True
  if week == -1:
    week = 0
  if disp: p('get_delta_days_weekday: dayInText, todayDayWeek =', dayInText, todayDayWeek)
  return days, week, todayDayWeek, dayInText, weekend, range_days

def get_number_period(doc, disp=False):
  if disp: p('get_number_period')
  days, week = NO_DAYS, 0
  for entity in doc:
    if disp: print(entity.pos_, entity.head, entity.lemma_)
    if entity.pos_=='NUM':
      if disp: print("found number "+entity.text)
      if entity.text.isdigit():
          num = int(entity.text)
      else:
          #num = textToNumbers.get(entity.text, NO_DAYS)
          num_str = convert(entity.text)
          num = int(num_str) if num_str.isdigit() else NO_DAYS
      if disp: print ('number is '+str(num))
      if nlp(str(entity.head))[0].lemma_ == 'week': # if there is week add it to number to week and if not match it num of days
        if num != NO_DAYS:
          week = num
      elif nlp(str(entity.head))[0].lemma_ == 'day': # new 05.07.2021
        days = num
  #if week > 0 and days == NO_DAYS:  days = 0
  return days, week

def check_date(dateText, disp=False, israel=False):
  days, week, found_days, cur_days = NO_DAYS, 0, NO_DAYS, NO_DAYS
  rangeDays, days2, week2 = 1, NO_DAYS, NO_DAYS
  todayDayWeek = 0 # get day in week today
  dayInText = -NO_DAYS # get day in week by text
  f_string = " days={0}, week={1}, days2={4}, found_days={2}, cur_days={3}"
  range_days, weekend = 1, False # single day
  first_day = True  # did not find a day of the week (to know when do we 2 days for a range)
  if len(dateText) == 0:
    return NO_DAYS, 0
  # spacy did seperate 'tuesday next week' into 2 parts 'tuesday' 'next week' and
  # our function uses the 'next week' and ignores the 'tuesday' so we force
  # a comma before and after
  for text in dateText: # check if we get several date variables
    if len(text) == 0: continue
    if disp: p('text =', text)
    #matcher = PhraseMatcher(nlp.vocab)
    for column in datesDf: # run on each column if there is match
      #listNlp = [nlp.make_doc(t) for t in df[column].tolist() if str(t) != 'nan']
      date_matcher = PhraseMatcher(nlp.vocab)
      date_matcher.add(column, None, *listNlp[column])
      #p(listNlp[column])
      doc = nlp(text)
      matches = date_matcher(doc)
      if disp: p(column, matches)
      numFinal = NO_DAYS
      if len(matches) > 0: # if we find match in the list of column
        match_words = ''
        for match_id, start, end in matches:
          match_words += f"{doc[start:end].text}, "
        if disp:
          p('col:',column)
          p("matchFound", match_words)
        if column == "nextWeek": # check if there
          if disp: p("is next Week")
          week = 1
          if days == NO_DAYS and found_days == NO_DAYS and not 'weekend' in match_words:
            days = 0
            numFinal = dateToNum.get(column, NO_DAYS)
          if disp: p(f"numFinal is {numFinal}, {days}")
          if 'weekend' in match_words:# and 'weekend' in text:  # match 'next week' to 'next week' because 'next' is in both
            if disp: p("is Weekend0", text, 'weekend' in text)
            range_days = 2
            weekend = True
        elif 'weekend' in match_words:# and 'weekend' in text:
          if disp: p("is Weekend", len(dateText), f'[{dateText}]', len(text) == 1)
          range_days = 2
          weekend = True
        if numFinal != NO_DAYS or days == NO_DAYS:
          days = numFinal
        #''' need this code for 'following day"
        if len(dateText) == 1 and not weekend:# and len(text) == 1: #even if the text consists of 2 words 'following day' since we found a match we can use the column index
          if disp: p(f"numFinal2 = {numFinal}")
          numFinal = dateToNum.get(column, NO_DAYS)
          if numFinal != NO_DAYS or days == NO_DAYS:
            return numFinal, range_days

        if disp: p(days, todayDayWeek, dayInText)
        # todayDayWeek is in the range 1=sunday to 7=saturday
        # dayInText is in the same range
        # in order to compare we need to convert both such the sunday = 8 (mon=1, tue=2...sat=7, sun=8)
        todayDayWeek_new = todayDayWeek if todayDayWeek > 1 else 8
        dayInText_new = dayInText if dayInText > 1 else 8
        if disp: p(days, todayDayWeek, dayInText, dayInText_new)
        if days != NO_DAYS:  # verify days match numOfdays (in case on Friday asked for "friday in 2 days" which is wrong)
          if column == "today" and days == 0:
            pass
          elif column == "tomorrow" and days == 1:
            pass
          elif column == "twoDays" and days == 2:
            pass
          elif column == 'thisweek' and (dayInText_new >= todayDayWeek_new):  # this week must be day after today up to sunday
            pass
          elif column == 'nextWeek' and week == 1:  # next week cannot have a contradiction because can be any day
            pass
          else:
            days = NO_DAYS
        cur_days = days  # days for this text independent of prev columns
        break # found a match no need to check other column for this text
    if disp: print("1." + f_string.format(days, week, found_days, cur_days, days2))
    if found_days == NO_DAYS: found_days = days
    if week == 0 and days == NO_DAYS and cur_days == NO_DAYS: # didn't find word in the DF dates

      days, week, todayDayWeek, dayInText, weekend, range_days = get_delta_days_weekday(text, dayInText, weekend, range_days, disp) # check day in week and return num of days and week

      if disp: print("2." + f_string.format(days, week, found_days, cur_days, days2))
      if days != NO_DAYS and days != found_days and found_days != NO_DAYS:
        days = NO_DAYS
      elif found_days == NO_DAYS:
        found_days = days
      if week == 0 or days == NO_DAYS:
        sav_days = days
        days, week = get_number_period(doc, disp) # check number of days/weeks
        if days == NO_DAYS and sav_days != NO_DAYS:
          days = sav_days
        if disp: print("3." + f_string.format(days, week, found_days, cur_days, days2))
        # in english the week ends on Sunday, so if we r on:
        # sunday then next_week=0 weeks from now
        # monday then next_week=1 weeks from now
        # -> we calc days up to sunday, and add 1 week
    if days2 == NO_DAYS:
      days2, week2 = get_number_period(doc, disp) # check number of days/weeks because "3 days", can be for two options, num of dasy and range
      if disp: print("3A. " + f_string.format(days, week, found_days, cur_days, days2))
      if week == 0 and days == NO_DAYS and days2 == NO_DAYS: # check if get format
        if disp: p("check date format", text)
        is_date, year, month, day, ndays = is_valid_date(text, disp)
        if disp:  p(f"4. get date by format {year}-{month}-{day} num of days = {ndays}")
        if is_date:
          days = ndays
          week = 0
        # if 2 named days (tuesday, sunday) means from tuesday to sunday)
      if days2 == NO_DAYS and days != NO_DAYS and text in dayInWeek:
        if first_day:
          first_day = False
        else:
          dayInText = dayInWeek[text]
          first_day = todayDayWeek + days
          if first_day > 7: first_day -= 7
          if disp: p('check range', text, dayInText, todayDayWeek, days, first_day)
          if todayDayWeek + days <= dayInText:
            days2 = abs(dayInText - todayDayWeek - days) + 1
          elif dayInText > first_day: # range of days that the second day is later (eg. sunday to tuesday)
            days2 = abs(dayInText - todayDayWeek + 7 - days) + 1
          else:  # the 2nd day is a week later
            days2 = (dayInText + 7 - todayDayWeek) + 7 - days + 1
  if disp: p(f"range = {days2}, number of days = {days}, weekend={weekend}")
  if days2 != NO_DAYS and days == NO_DAYS:
    if disp: p("dates with just number of days/week")
    days = days2
    week = week2
  if days2 != NO_DAYS and days != NO_DAYS:
    if disp:  p("get range", week2, days2, days, len(dateText), weekend, dateText)
    rangeDays = days2 + week2 * 7
  if (len(dateText) == 1 and not weekend and
         'next' not in dateText[0]): # in case 'next 2 days'
    rangeDays = 1
  elif weekend:
    rangeDays = range_days
  elif days == days2 and rangeDays == days and 'next' in ', '.join([s for s in dateText]):  # in case 'next 2 days'
    days = 0
  range_days = rangeDays

  if disp: p("5. " + f_string.format(days, week, found_days, cur_days, range_days))
  if disp: p('todayDayWeek', todayDayWeek, dayInText, days, weekend)
  org_days = days
  if todayDayWeek == 0 or (days == found_days == cur_days == -dayInText == NO_DAYS):  # no day information -> today
    if TODAY == 0:
      days = get_todayDayWeek()
    else:
      days = TODAY
    todayDayWeek = dayInText = days
    found_days = days = 0 # to convert to #days from saturday (0 if saturday, 1=sunday etc)
    if disp: p('u:', todayDayWeek, dayInText, days, found_days)
  if days != NO_DAYS and days != found_days and found_days != NO_DAYS:
    days = NO_DAYS
  elif days != NO_DAYS and found_days == NO_DAYS:
    found_days = days
  elif days == NO_DAYS and week > 0:
    days = found_days
    if days == NO_DAYS:
      days = 0 # no day is specified so days = 0 (number of days since today)
  if days != NO_DAYS:
    if disp: p(todayDayWeek, dayInText)
    # convert to english weekday number (monday=1... sunday=7)
    todayDayWeek = todayDayWeek - 1 if todayDayWeek > 1 else 7 # from our day sunday=1,.. saturday=7
    dayInText =  dayInText - 1 if dayInText > 1 else 7
    if disp: p('y:', todayDayWeek, dayInText, week, days)
    if todayDayWeek > dayInText and week > 0:
      week -= 1
    if range_days == 2 and weekend:
      if disp: p('weekend', days, org_days)
      if org_days == NO_DAYS or dayInText >= 6:
        if dayInText == 7: # if sunday there is one day left in the weekend
          if israel: # sunday is not the weekend in israel, only saturday
            days = NO_DAYS
          elif week == 1: # next week
            days -= 1 # nextweekent starts on Saturday
          else:
            range_days = 1
        elif dayInText < 6: # not sunday and not staurday
          days = 6 - dayInText # number of days to saturday
          if israel: range_days = 1
      elif len(dateText) > 1:  # must have more than one word (was gettuing here with 'next weekedn' only)
        days = NO_DAYS  # can not say 'monday, next weekend
    if days != NO_DAYS:
      return week * 7 + days, range_days
  return NO_DAYS, 0

def check_gpe(entity, ents, ent_text, gpe, multiple_cities, DEBUG):
        token = None
        for e in ents:
          if ent_text == e[0]:
            token = e[1]
            break
        # verify the GPE is a true GPE for cases that a city has a name that has another meaninig
        if token and token.text != token.lemma_: # a true GPE cannot be lemmatized
          return 'continue', gpe, 0

        # for example there is a city in Denemark that has a name 'rain'
        if token and len(ents) > 1 and (token.head == token or token.pos_ not in ['PROPN', 'PRON', 'NOUN']) and not entity._.is_country:
          valid_gpe = False
          for e in ents:
            if ent_text != e[0]:
              tk = e[1]
              if tk.head == token:  # the token is connected to another gpe, so it is a valid gpe (for example, (paris, canada) are connected
                valid_gpe = True
                break
#                return 'break', gpe, 0
          if not valid_gpe:
            if DEBUG: p('A:', ent_text)
            return 'continue', gpe, 0

        ent_type = 'state'
        if DEBUG: p('0:', ent_text, entity._.is_city, entity._.is_country)
        if entity._.is_city and not entity._.is_country: # 'canada' is a country and also a city in Portugal
          ent_type = 'city'
          if ent_text in df_CITIES_API.index:
            code_country = df_CITIES_API.loc[ent_text].country
            if type(code_country) != str:
              multiple_cities = True
              # see note why not to use code_country[0] which sometimes give 'Key Error'
              # https://stackoverflow.com/questions/46153647/keyerror-0-when-accessing-value-in-pandas-series
              ent_country = countries_df.loc[code_country.iloc[0]].Name
            else:
              ent_country = countries_df.loc[code_country].Name
          #elif ent_text in CITIES_IL:
          #  ent_country = 'israel'
          else:
            ent_country = ''
        elif entity._.is_country or ent_text in CITIES_API_country_code:
          ent_type = 'country'

        if ent_type not in gpe:
          gpe[ent_type] = []
        if ent_type == 'city':
           gpe[ent_type].append((entity.text, ent_country))
        else:
          gpe[ent_type].append(entity.text)
        return None, gpe, multiple_cities

def get_city_country(multiple_cities, gpe, DEBUG, LANG):
  if DEBUG: p('1:', multiple_cities, gpe)
  if multiple_cities or ('city' in gpe and len(gpe['city']) > 1):
    if 'country' in gpe:
      # verify country code of the city is correct, when there multiple cities
      for i, (city, city_country) in enumerate(gpe['city']):
        country = gpe['country'][0]
        if city_country != country:
          for code_country in df_CITIES_API.loc[city].country:
            if city_country == countries_df.loc[code_country].Name:
              # found a matching country
              gpe['city'][i] = (city, country)
              break
    else:
      check_capital = True
      if len(gpe['city']) == 2: # maybe enter a country which has city with that name (eg. Toronto, US = there is a city name 'us' in france and 'usa' in japan)
        # 'city': [('toronto', 'Canada'), ('us', 'france')]
        for i in range(1,-1,-1):
          city = gpe['city'][i][0].upper()
          if city in countries_df.index: #usually the 2nd "city" is the country
            city_country = countries_df.loc[city].Name
            if type(city_country) == pd.Series:
              city_country = city_country.iloc[0]
            j = 0 if i == 1 else 1
            gpe['city'] = [(gpe['city'][j][0], city_country)]
            gpe['country'] = city_country
            check_capital = False
            break
      if check_capital:
        # check if one of the cities is a capital or a large city, then use it
        #p(gpe, multiple_cities)
        for i, (city, city_country) in enumerate(gpe['city']):
          if city in capitals_df.index.values:
            # found a matching country
            city_country = capitals_df.loc[city].country
            if type(city_country) == pd.Series:
              city_country = city_country.iloc[0]
            gpe['city'][i] = (city, city_country)
            break
          if city in largest_df.index.values:
            # found a matching country
            city_country = largest_df.loc[city].country
            gpe['city'][i] = (city, city_country)
            break
  elif 'country' in gpe and 'city' in gpe:  # country with city, verify correct
      if DEBUG: p('2:', gpe)
      # verify country code of the city is correct, when user entered
      city, city_country = gpe['city'][0]
      country = gpe['country'][0]
      if city_country != country:
        gpe['city'] = [(city, "ERROR: " + MESSAGES[LANG]["messages"]["city_error"].format(city, country))]
  elif 'country' in gpe and 'city' not in gpe:  # country without city, get the capital
    country = gpe['country'][0]
    #p(country)
    if country in CAPITALS:
      gpe['city'] = [(CAPITALS[country], country)]
  return gpe, multiple_cities

def get_parts(text, DEBUG, LANG, disp=False, verbose=True):
  date, time, gpe, ents, ents_d = [], [], {'action':[]}, [], []
  multiple_cities = False
  if disp: p()
  round = 0
  while round < 2:
      doc = nlp(text)#.translate(remove_punct_dict))
      for token in doc:
        if disp:
          p(f"Tokens of [{token.text}]: dep_={token.dep_}, ent_type={token.ent_type_}, head={token.head}, lemma_={token.lemma_}, pos_={token.pos_}, tag_={token.tag_}, is_action={token._.is_action}")
        if token._.is_action:  # checking for action first catch cities with the same name ('rain' is a city)
          tag = ACTIONS[token.lemma_]
          tag_exists = [t for t in gpe['action'] if t[0] == tag]
          if len(tag_exists) == 0:
            gpe['action'].append((tag, token.lemma_))
        elif token.ent_type_ == 'GPE': ents.append((token.text.lower(), token))
        elif token.ent_type_ in ['DATE', 'TIME', 'CARDINAL']: ents_d.append((token.text.lower(), token))
      for entity in doc.ents:
          if disp:
            p(f"Entities of [{entity.text}]: {entity.label_}='{spacy.explain(entity.label_)}', is_city={entity._.is_city}, is_country={entity._.is_country}")
          ent_text = entity.text.lower().translate(remove_punct_dict)
          if entity.label_ in ['DATE', 'TIME', 'CARDINAL']:
            if len(ent_text.split()) > 0: # take care of the case 'wednesady next week' without comma
              token = None
              for e in ents_d:
                if e[0] in ent_text:
                  token = e[1]
                  if token.text in dayInWeek or token.text in dateToNum: # a seperate entity
                    if token.text not in date:
                        date.append(token.text)
              idx0 = 0
              ent_t = ent_text
              for word in ent_text.split(): # take care of "July 10 for 3 days" without comma
                if word in stopwords:
                  idx1 = ent_text.find(word)
                  if idx1 < 0 :continue # not found
                  if idx1 == 0: continue #  first word of the sentence, so no need to treat as if no comma
                  if ent_text[idx0:idx1-1] not in date:
                    date.append(ent_text[idx0:idx1-1])
                  idx0 = idx1 + len(word) + 1
                  ent_t = ent_text[idx0:]
              ent_text = ent_t

            if len(ent_text.split()) > 1 or len(date) == 0:
                if ent_text not in date:
                    date.append(ent_text.lower())
          '''
          if entity._.is_action:  # 'rain' is both a city and weather action
            tag = ACTIONS[ent_text]
            gpe['action'].append((tag, ent_text))
          '''
          if entity.label_ == 'GPE':
            act, gpe, multiple_cities = check_gpe(entity, ents, ent_text, gpe, multiple_cities, DEBUG)
            if act == 'continue': continue
            if act == 'break': break

      gpe, multiple_cities = get_city_country(multiple_cities, gpe, DEBUG, LANG)
        # remove city with same name as action ('rain') if there is another city
      if 'city' in gpe:
          org_gpe = gpe['city'].copy() # copy because the list is modified inside the loop
          for tup in org_gpe:
            city = tup[0]
            city_exists = [t for t in gpe['action'] if t[0] == city or t[1] == city]
            if len(city_exists) == 0: continue
            if len(gpe['city']) == 1:  # must leave at least one city
              # remove from action list if appears only once in the sentence
              n = [t for t in doc if t.text == city]
              if len(n) > 1: continue
              gpe['action'].remove(city_exists[0])
              continue
            gpe['city'].remove(tup)

      if len(gpe['action']) > 0:
        #  gpe['action'] = [('all', 'weather')]
        #else:
        for i, tup in enumerate(gpe['action']):
          if tup[0] == 'all':
            if i == 0: break
            gpe['action'].remove(tup)
            gpe['action'].insert(0, tup)
            break

      # when the city has 2 words sometimes space did not recognize date
      # in such case we remove the city and do another round
      if 'city' in gpe and len(date) == 0 and len(time) == 0 and len(gpe['city'][0][0]) > 1:
        org_text = text
        text = text.replace(gpe['city'][0][0], '')
        round += 1
        if disp: p(f"doing round 2 in get_parts {gpe}, {org_text}, {text}")
        continue
      break

  result = {'date':date, 'time':time} if len(date) > 0 and len(time) > 0 else {'time':time} if len(time) > 0 else {'date':date}
  result.update(gpe)

  if disp:
    p(result)
  elif verbose and 'city' not in result:
    p(f'FAILED: org [{text}], {result}')
  return result

"""# Run the bot"""

## Google search

def get_google(text):
  one_word = False
  if len(text.split()) == 1: # one word sometimes did not give results (such as 'נטק')
    text += ' ' + text
    one_word = True
  url = "https://google.com/search?q=" + text + '&hl=en'
  request_result = requests.get(url)
  soup = bs4.BeautifulSoup(request_result.text.lower(), "html.parser")
  spans = soup.find_all('span', class_='BNeawe')
  new_text = ''
  for span in spans:
    if isinstance(span.contents[0], bs4.NavigableString):
      new_text += str(span.contents[0]) + ' '
  if new_text == '':
    divs = soup.find_all('div', class_="muxgbd v0nncb lylwlc")
    for div in divs:
      if 'did you mean: ' in div.text:
        new_text = div.text[14:]
      elif 'showing results for' in div.text:
        idx1 = div.text.find("q='")
        idx2 = div.text[idx1 + 3:].find("'")
        new_text = div.text[idx1 + 3: idx1 + 3 + idx2]
  if one_word and len(new_text.split()) > 1:
    new_text = new_text.split()[0]
  return new_text   #, soup, request_result, spans, divs
#get_google("wether in tel aviv")
#get_google("'קשאיקר אםגשט ןמ ןדרשקך")'weather in tel aviv
#get_google("נטק") 'bye'

def google_detect(user_msg):
  if googletrans_api:
    return translator.detect_language(user_msg)["language"]
  else:
    return translator.detect(user_msg).lang

def google_translate(user_msg_, dest='en', VERBOSE=False):
  user_msg = translator.translate(user_msg_, dest)
  if googletrans_api:
    if VERBOSE:  p(f"{user_msg['input']} ({user_msg['detectedSourceLanguage']}) --> {user_msg['translatedText']} ({dest})")
    return user_msg["translatedText"]
  else:
    if VERBOSE:  p(f"{user_msg.origin} ({user_msg.src}) --> {user_msg.text} ({user_msg.dest})")
    return user_msg.text

def add_language(lang):
  lang_exists = [t for t in MESSAGES_lang if t == lang]
  if len(lang_exists) > 0:
    p(f'{lang} already exists')
    return
  MESSAGES_lang.append(lang)
  p(MESSAGES_lang)

  MESSAGES.update({lang:{'messages':{}}})
  if googletrans_api:
    for k, v in MESSAGES_en.items():
      if type(v) == list:
        msg_new = translator.translate(v, lang)
        ar = []
        for msg in msg_new:
          ar.append(msg["translatedText"])
        MESSAGES[lang]["messages"].update({k: ar})
        continue
      MESSAGES[lang]["messages"].update({k: google_translate(v, dest=lang)})
  else:
    new_msg = list(translator.translate(list(MESSAGES_en.values()), dest=lang))
    for i, k in enumerate(MESSAGES_en.keys()):
      if type(new_msg[i]) is list:
        for msg in new_msg[i]:
          MESSAGES[lang]["messages"].update({k: msg.text})
        continue
      MESSAGES[lang]["messages"].update({k: new_msg[i].text})
  #p(MESSAGES[lang])

  intents.update({lang:{'messages':[]}})
  msg_arr, i = [], 0
  if not googletrans_api:
    new_msg = translator.translate(list(intents_en), dest=lang)
  for dict_ in intents['en']['messages']:
    resp, msg = [], {}
    for k, v in dict_.items():
      if k == 'tag' or k == 'patterns':  # no translation
        msg.update({k: v})
        continue
      if googletrans_api:
        msg_new = translator.translate(v, lang)
        for m in msg_new:
          resp.append(m["translatedText"])
      else:
        for j in range(len(intents['en']["messages"][i]["responses"])):
          resp.append(new_msg[i][j].text)
    msg.update({"responses": resp})
    msg_arr.append(msg)
    i += 1
  intents[lang].update({"messages": msg_arr})  # save the new langauge

  new_d = {"intents": {"language": {lang: {'messages': {}}}},
          "messages": {"language": {lang: {'messages': {}}}}}
  new_d['intents']['language'][lang] = intents[lang]
  new_d['messages']['language'][lang] = MESSAGES[lang]
  # read old new langaued that were not yet added to main messages file
  list_d = []
  try:
    with open(path + 'new_messages.json', "r") as f:
      list_d = json.loads(f.read())
  except Exception as error:
    pass
    p(error)
  list_d.insert(0, new_d) #append(new_d)
  #list_d)
  with open(path + 'new_messages.json', "w") as f:
    json.dump(list_d, f, indent=1, ensure_ascii = False)
#add_language('he')
#translator.detect('الشغل'))

# 'xab' is in Hmong langauge (hmn)
#translator.detect('Работа'))
#add_language('iw') # hebrew
#add_language('ar') # arabic
#add_language('ru') # russian
#add_language('fr')

def update_session(LANG, RUN_TEST, switched_lang, error='', new_lang='', org_msg='', url_icon='', YES_NO=False, yes_addition=''):
      session['error'] = error
      session['lang'] = LANG
      session['new_lang'] = new_lang
      session['user_msg'] = org_msg
      session['RUN_TEST'] = RUN_TEST
      session['switched_lang'] = switched_lang
      session['url_icon'] = url_icon
      session['YES_NO'] = YES_NO
      session['yes_addition'] = yes_addition

def run_bot(user_msg, VERBOSE, LANG, new_lang, org_msg):
    do = True
    NOANSWER, YES = 3, 7
    min_similarity = 0.84
    DEBUG = VERBOSE
    error = ''
    RUN_TEST = session['RUN_TEST']
    switched_lang = session['switched_lang']
    YES_NO = session['YES_NO']
    yes_addition = session['yes_addition']

    while do:

      if RUN_TEST > 0:
        YES_NO = False
        user_msg = QUESTIONS[LANG][RUN_TEST- 1]
        RUN_TEST += 1
        VERBOSE = 0
        if RUN_TEST > len(QUESTIONS[LANG]): RUN_TEST = 0
        p(user_msg)

      #user_msg = input().lower().strip()

      if user_msg == '':
        answers = intents[LANG]["messages"][NOANSWER]['responses']

        update_session(LANG, RUN_TEST, switched_lang)
        return random.choice(answers), False

      if user_msg == 'run test':
        if LANG not in ['en', 'he']:
            LANG = 'he'
        RUN_TEST = 1
        continue

      responses_yes = intents[LANG]["messages"][YES]['responses']
      if new_lang != '':
        if user_msg in responses_yes or google_translate(user_msg) in responses_yes:
          if new_lang not in MESSAGES_lang:
            add_language(new_lang)
          LANG = new_lang
          switched_lang = True
        user_msg = org_msg
        new_lang = ''
        YES_NO = False
      else:
          response = google_detect(user_msg)
          if response != LANG:
              p(response)
              if response in ['en', 'he', 'iw']:
                LANG = response if response == 'en' else 'he'
                switched_lang = True
              else:
                verify = True
                if response not in MESSAGES_lang:
                    # add langauge only when sure - of at least 3 words of length 5 letters each - to prevent erroneous detection
                  sentence = ' '.join(filter(None, user_msg.split(' ')))
                  if not (len(sentence) > 11 and len(user_msg.split()) > 2):
                    verify = False  # False "new langauge" - google think that 'haifa israel' is in arabic, and 'Paris, frnace' is in french
                if verify:
                  new_lang = response
                  answer = MESSAGES[LANG]["messages"]["new_lang"].format(new_lang.upper())
                  update_session(LANG, RUN_TEST, switched_lang, new_lang=new_lang, org_msg=user_msg, YES_NO=True)
                  return answer, False

          elif LANG == 'en': # check if the google translate stopped working
              test = google_detect('שלום וברכה')
              if test == LANG:
                error = 'Note: Google translate stopped working temporarily -> multi-lingual option is not functional'
                p(error)

      round = 0
      answer = ''
      if YES_NO:
        if user_msg in responses_yes or google_translate(user_msg) in responses_yes:
            user_msg = org_msg + yes_addition
        yes_addition = ''
        YES_NO = False

      org_msg = user_msg
      tag, url_icon = '', ''
      while round < 4 and do:
        days, parts = NO_DAYS, ''
        if LANG != 'en' and round == 0:  # no use to run this code using non english input
            round = 1
        else:
            if VERBOSE:   p(f'round {round}: {user_msg}')
            doc1 = nlp(user_msg)
            answers, tag = None, None
            top_similarity = 0
            # verify not an erroeous finding (if we have GPE in the doc we assume it is not a general request)
            if len([ent for ent in doc1.ents if ent.label_ == 'GPE']) == 0 or len([tk for tk in doc1 if tk.like_email]) > 0:
              for ints in intents[LANG]["messages"]:
                #p(ints)
                for text in ints['patterns']:
                  doc2 = nlp(text)
                  if doc1.vector_norm == 0 or doc2.vector_norm == 0:
                    continue
                  # Get the similarity of doc1 and doc2
                  similarity = doc1.similarity(doc2)
                  if VERBOSE > 2: p(f"{similarity}, {doc2}, {[ints['tag']]}")
                  if similarity > top_similarity:
                    top_similarity = similarity
                    answers = ints['responses']
                    tag = ints['tag']
            #  p(top_similarity, tag)
            #  p(answers)
              shift = 3 if tag == "mail" else 0
              if top_similarity > min_similarity - shift:
                if tag == "goodbye":
                  do = False
                if tag in ["goodbye", "greeting", "thanks", "options"]:
                  answer = random.choice(answers)
                  break
                if tag == "mail":
                  to = [tk for tk in doc1 if tk.like_email][0]
                  id = intents[LANG]["messages"][5]["responses"][6]
                  conv = intents[LANG]["messages"][5]["responses"][7]
                  df_chat = pd.DataFrame(session['df_chat'], columns=['index', id, conv])
                  df_chat_html = (df_chat.style
                            .set_properties(subset=['index'], **{'font-weight': 'bold'})
                            .set_properties(subset=[conv], **{'width': '500px'})
                            .set_properties(subset=['index'], **{'width': '20px'})
                            .hide_index()
                            .render()
                            .replace('index','')
                            )
                  html = render_template('chatbot_4email.html', df_chat=df_chat_html, length=len(df_chat), lang=LANG)
                  rtl = 'rtl' if LANG in ['he', 'iw', 'ar'] else ''
                  html.replace('<html',f'<html dir="{rtl}" lang="{LANG}"')
                  if not send_email(text=html, subject='Log from WeatherBot', to=to, ip=request.headers['X-Real-IP']):
                    answer = f"Failed to send email to [{to}]"
                  else:
                    answer = random.choice(answers)
                  break
    #        if round == 2 and session['google']: round = 3 # to know we got the answer from get_parts()
            parts = get_parts(user_msg.lower(), DEBUG, LANG, VERBOSE > 1, False) # need to use lower() because google might return in capitalization
            if VERBOSE:  p('x:', parts, round, LANG, switched_lang)
            if len(parts.get('date')) > 0:
              if 'city' in parts and 'ERROR' not in parts['city'][0][1]:
                israel = parts.get('city')[0][1] == 'israel'
              days, range_days = check_date(parts['date'], VERBOSE, israel=israel)
              if VERBOSE:  p(days, range_days)
              if days > 8:
                answer = MESSAGES[LANG]["messages"]["date_outof_range"]
                break
              else:
                if days + range_days > 8:
                  range_days = 7 - days
                if range_days == 0: range_days = 1
                if VERBOSE:  p(days, range_days)
        if days != NO_DAYS and 'city' in parts and 'ERROR' not in parts['city'][0][1] and len(parts.get('action')) > 0:
          if VERBOSE:  p(round, parts)
          answer, url_icon = get_weather(days, parts['city'], parts['action'], range_days, LANG)
          break
        elif 'city' in parts and 'ERROR' in parts['city'][0][1] and not switched_lang:  #to try google for gibrish
          answer = parts['city'][0][1]
          break
        elif round == 0:
          round = 1
          user_msg = ''
          space = ' '
          for token in doc1:
            if token.text in stopwords: continue
            text = token.text.lower().translate(remove_punct_dict)
            if text == '': continue
            if text[-1] == '-': # take care of 'ra- anana'
              user_msg += space + text[:-1]
              space = ''
            else:
              user_msg += space + text
              space = ' '
          continue
        elif round == 1:
          round = 2
          if LANG != 'en':  #No need to translate english (otherwise, remove special chars that might return non ascii code suach as apostophy that returns &#39)
              user_msg = google_translate(org_msg.translate(remove_punct_dict), VERBOSE=VERBOSE) # default translation is to english - can set source/dest langauge: src="de"/ dest="he"
              if user_msg != '':
                continue
        if round == 2:
          round = 3
          user_msg = get_google(org_msg)
          if user_msg != '':
            continue
        break
      color = False
      if answer == '':
        color = True
        if parts.get('city', '') == '':
          answer = MESSAGES[LANG]["messages"]["city_unknown"]
        elif len(parts.get('action', '')) == 0:
          answer = MESSAGES[LANG]["messages"]["action_unknown"]
        else: # if 'date' not in parts or len(parts['date']) == 0:
          answer = MESSAGES[LANG]["messages"]["date_unknown"]
      else:
        #p('round: ', round, (round >= 2 and not 'ERROR' in answer))
        if round >= 2 and not 'ERROR' in answer and session['google']:
          answer += f' ({MESSAGES[LANG]["messages"]["from_google"]})'
      if color:
        answer = f'<div style="color: red;">{answer}</div>'
        city = parts.get('city','') if parts.get('city','') != '' else ''
        action = parts.get('action', '') if len(parts.get('action', '')) > 0 else ''
        date = parts.get('date', '') if len(parts.get('date', '')) > 0 else ''
        answer = MESSAGES[LANG]["messages"]["error_current"].format(answer, city, action, date)
        if city != '':
          if date == '':
            date = "'Today'"
            if LANG != 'en': date = f"'{google_translate('Today', dest=LANG)}'"
          else: ''
          if action == '':
            action = "'Weather'"
            if LANG != 'en': action = f"'{google_translate('Weather', dest=LANG)}'"
          else: action = ''
          if date != '' and action != '':
            date += ', '
          answer = f'{answer}<br><div style="color:DodgerBlue;">{MESSAGES[LANG]["messages"]["error_option"].format(date, action)}</div>'
        YES_NO = True
        if type(date) == str:  date = date.replace("'","")
        if type(action) == str:  action = action.replace("'","")
        yes_addition = f',{date}{action}'
      update_session(LANG, RUN_TEST, switched_lang, org_msg=org_msg, error=error, url_icon=url_icon, YES_NO=YES_NO, yes_addition=yes_addition)
      return answer, tag=="goodbye"


