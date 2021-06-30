# echo > /var/log/drbarak.pythonanywhere.com.error.log

from flask import render_template, redirect, request
from flask_app import session

from prog.forms import ChatForm

import spacy, random, requests, bs4, time, json
from dateutil.parser import parse
from datetime import date

import pandas as pd

from prog.chatbot_init import nlp, stopwords, remove_punct_dict, space_punct_dict, api_key, URL, translator, path, icon_url
from prog.chatbot_init import df_CITIES_API, CITIES_API_country_code
from prog.chatbot_init import largest_df, countries_df
from prog.chatbot_init import cities_il_df, CITIES_IL
from prog.chatbot_init import capitals_df, CAPITALS
from prog.chatbot_init import ACTIONS#, ACTIONS_patterns, ACTIONS_tags
from prog.chatbot_init import MESSAGES_lang, MESSAGES, MESSAGES_en, intents, intents_en
from prog.chatbot_init import p, send_email

IDLE_TIME = 60 * 30 # max half an hour between questions to the bot

def chatbot():
    if 'chat_' not in session:
        p()
        p('------------------------------')
        p('Start ChatBot', spacy.__version__)
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

        send_email()
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

        if 'time' in session:
            session_time = session['time']
            delta = time.time() - session_time
            if delta > IDLE_TIME or session['index'] == 0:
                session['df_chat'] = []
                session['time'] = time.time()
                session['index'] = 1
                session['google'] = False
                session['clear'] = False
            else:  # reset the session time as long as no delay of more than idle_time
                session['time'] = time.time()
        else:
            session['df_chat'] = []
            session['time'] = time.time()
            session['google'] = False
            session['index'] = 1
            session['clear'] = False

    LANG = session['lang']
    new_lang = session['new_lang']
    user_msg = session['user_msg']

    id = intents[LANG]["messages"][5]["responses"][6]
    conv = intents[LANG]["messages"][5]["responses"][7]
    df_chat = pd.DataFrame(session['df_chat'], columns=['index', id, conv])
    form = ChatForm()
    error = ''
    if request.method == 'POST':
        #p('debug', session['debug'], form.google.data, form.debug.data)
        if form.run_bot.data:
            user_msg, answer, goodbye, LANG, new_lang, error, url_icon = run_bot(form.user_msg.data, session['debug'], LANG, new_lang, user_msg)
            session['error'] = error
            session['lang'] = LANG
            session['new_lang'] = new_lang
            session['user_msg'] = user_msg
            if session['clear']:
                session['index'] = 1
                session['df_chat'] = []
                session['clear'] = False
            index = session['index']
            id = intents[LANG]["messages"][5]["responses"][6]
            conv = intents[LANG]["messages"][5]["responses"][7]
            bot = intents[LANG]["messages"][5]["responses"][5]
            you = intents[LANG]["messages"][5]["responses"][4]
            session['df_chat'] = [[index + 1, bot + ': ', answer], [index, you + ': ', user_msg]] + session['df_chat']
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
            p('debug', session['debug'])
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
    html = render_template('chatbot.html', title='CHAT BOT', form=form, error=session['error'], df_chat=df_chat_html, length=len(df_chat), debug=session['debug'], google=session['google'],
                                prompts=intents[LANG]["messages"][5]["responses"])
    rtl = 'rtl' if LANG in ['he', 'iw', 'ar'] else ''
    return html.replace('<html',f'<html dir="{rtl}" lang="{LANG}"')

def call_web(city_name, country_code, fahrenheit, count, LANG):
    state = ''
    p('in call_web')
    api_url = f"{URL}q={city_name},{state},{country_code}&units={'metric' if not fahrenheit else 'imperial'}&lang={LANG}&appid={api_key}".format('weather')
    if count > 1:
      cor = df_CITIES_API.loc[city_name].coord
      if type(cor) is not  dict: #more than one record for that city
        for index, row in df_CITIES_API.loc[city_name].iterrows():
          if country_code == row['country'] or country_code == '': # if no country code then use the first entry
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
        print(MESSAGES[LANG]["messages"]["web_error"].format(response.status_code, api_url))
        p(response_dict['message'])
        return None

def get_weather_info(actions, count, cnt, city_weather, default, LANG):
  all_action = actions[0][0] == 'all'  # always first
  #p(all_action)
  result = ''
  for action in actions:
    tag = action[0]
    if tag == "fahrenheit": continue
    user_act = action[1]
    if count < 2:
      data = city_weather if tag == "all" else city_weather['main'] \
        if tag in ["weatherTemp", "weatherPressure", 'temp', "pressure", "humidity"] else \
              city_weather['sys'] if tag == "sunrise" else city_weather['wind'] \
              if tag in ["weatherWind", "wind"] else city_weather[tag]
    else:
      data = city_weather
    #p('in loop', user_act, tag, data)
    if tag in ['clouds']:
      clouds_percentage = data['all'] if count < 2 else data['clouds']
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
      data_tag = data['main'] if tag == 'all' and count < 2 else data
      #p(count, tag, data_tag, data)
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
            if count > 1  and cnt == 0:
              break
          elif i == 2: info = data_tag["temp_min"] if cnt == 0 else data_tag["temp"]["min"]
          elif i == 3: info = data_tag["temp_max"] if cnt == 0 else data_tag["temp"]["max"]
          result += f' {temp} = {info},'
      if tag in ["weatherPressure", "pressure", "all"]:
        result += f' {MESSAGES[LANG]["messages"]["pressure"]} = {data_tag["pressure"]},'
      if tag in ["humidity", "all"]:
        result += f' {MESSAGES[LANG]["messages"]["humidity"]} = {data_tag["humidity"]},'
    if tag in ["wind", "weatherWind", "all"]:
      data_tag = data['wind'] if tag == 'all' and count < 2 else data
      for i, wind in enumerate(MESSAGES[LANG]["messages"]["wind"]):
        if i == 0: info = data_tag["speed"] if count < 2 else data_tag["wind_speed"]
        elif i == 1: info = data_tag["deg"] if count < 2 else data_tag["wind_deg"]
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
        data_tag = data['visibility'] if tag == 'all' or count > 1 else data
      result += f' {MESSAGES[LANG]["messages"]["visibility"]} = {data_tag},'
    if tag in ["sunrise","all"]:
      data_tag = data['sys'] if tag == 'all' and count < 2 else data
      for i, wind in enumerate(MESSAGES[LANG]["messages"]["sunrise"]):
        if i == 0: info = data_tag["sunrise"]
        elif i == 1: info = data_tag["sunset"]
        result += f' {wind} = {time.strftime("%H:%M:%S", time.gmtime(info + 3 * 60 * 60))},'
  return result

def get_weather(dt, location, actions, LANG, count=2):
  #p(dt, location)
  city_w = city = location[0][0]  # assume one city (not handling if there are 2 cities)
  #p(city, city_w)
  result = ''
  # check if city in api_city list
  if city in df_CITIES_API.index.values:
    result = df_CITIES_API.loc[city]
  if len(result) == 0: # not found, get district
    if city in cities_il_df.index.values:
      city_w = cities_il_df.loc[city].district
  elif len(result) > 0: # more than one city -> need country
    pass

  #p(city_w, location)
  country = location[0][1].lower()
  #p(country, len(countries_df.Name), country in list(countries_df.Name))
  if country in list(countries_df.Name):
    country_code = countries_df[countries_df.Name == country].index[0]
  else:
    country_code = ''
  #p(city_w, country_code)#

  fahrenheit = True if len([action for action in actions if action[0] == "fahrenheit"]) > 0 else False
  #p('in get_weather:', fahrenheit)
  city_weather_resp = call_web(city_w, country_code, fahrenheit, count, LANG)

  if city_weather_resp is None:
    return MESSAGES[LANG]["messages"]["api_error"], ''
    # check what informtion the user asked for

  #p(city_weather_resp)
  city_weather = city_weather_resp if count < 2 else city_weather_resp["current"]
  #p(city_weather)

  default = city_weather["weather"][0]["description"]
  icon = city_weather["weather"][0]["icon"]
  url_icon = f"{icon_url}".format(icon)
  result = ''

  for cnt in range(count):
    if cnt > 0:
      # bug in python - cannot have r += z + x if cond else y
      M = MESSAGES[LANG]["messages"]["web_days_msg"].format(cnt) if cnt > 1 else MESSAGES[LANG]["messages"]["web_day_msg"]
      result += '<br>' + M
      city_weather = city_weather_resp["daily"][0]
    new_result = get_weather_info(actions, count, cnt, city_weather, default, LANG)
    result += new_result

  if result == '': result = default
  if result[-1] == ',': result = result[:-1]
  country = location[0][1]
  if LANG != 'en': # in case there are parts of the answer which are not in the proper langauge
    response = translator.translate(city, dest=LANG) # need to separet ity from country in case one of them has multi words and google doe not keep the qoutation mark as needed
    #response = translator.translate(f"({city}, {country})", dest=LANG)
    #city, country = response.text
    p(f"{response.origin} ({response.src}) --> {response.text} ({response.dest})")
    city = response.text
    response = translator.translate(country, dest=LANG)
    country = response.text
  response =  MESSAGES[LANG]["messages"]["web_msg"].format(city.capitalize(), country.capitalize(), result)
  return response, url_icon

"""# Get Parts (POS)"""

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
                return 'break', gpe, 0
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
          elif ent_text in CITIES_IL:
            ent_country = 'israel'
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
  doc = nlp(text.lower().translate(remove_punct_dict))
  date, gpe, ents = [], {'action':[]}, []
  multiple_cities = False
  if disp: p()
  for token in doc:
    if disp:
      p(f"Tokens of [{token.text}]: dep_={token.dep_}, ent_type={token.ent_type_}, head={token.head}, lemma_={token.lemma_}, pos_={token.pos_}, tag_={token.tag_}, is_action={token._.is_action}")
    if token._.is_action:  # checking for action first catch cities with the same name ('rain' is a city)
      tag = ACTIONS[token.lemma_]
      tag_exists = [t for t in gpe['action'] if t[0] == tag]
      if len(tag_exists) == 0:
        gpe['action'].append((tag, token.lemma_))
    elif token.ent_type_ == 'GPE': ents.append((token.text.lower(), token))
  for entity in doc.ents:
      if disp:
        print(f"Entities of [{entity.text}]: {entity.label_}='{spacy.explain(entity.label_)}', is_city={entity._.is_city}, is_country={entity._.is_country}")
      ent_text = entity.text.lower().translate(remove_punct_dict)
      if entity.label_ == 'DATE': date.append(ent_text)
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

  if len(date) == 0:
    date = 'current'
  if len(gpe['action']) == 0:
    gpe['action'] = [('all', 'weather')]
  else:
    for i, tup in enumerate(gpe['action']):
      if tup[0] == 'all':
        if i == 0: break
        gpe['action'].remove(tup)
        gpe['action'].insert(0, tup)
        break

  result = {'date':date}
  result.update(gpe)

  if disp:
    p(result)
  elif verbose and 'city' not in result:
    p(f'FAILED: org [{text}], {result}')
  return result

"""# Run the bot"""

## Google search

def get_google(text):
  url = "https://google.com/search?q=" + text + '&hl=en'
  request_result = requests.get( url )
  soup = bs4.BeautifulSoup(request_result.text, "html.parser")
  spans = soup.find_all('span', class_='BNeawe')
  new_text = ''
  for span in spans:
    if isinstance(span.contents[0], bs4.NavigableString):
      new_text += str(span.contents[0]) + ' '
  return new_text
#get_google("wether in tel aviv")

def add_language(lang):
  lang_exists = [t for t in MESSAGES_lang if t == lang]
  if len(lang_exists) > 0:
    p(f'{lang} already exists')
    return
  MESSAGES_lang.append(lang)
  p(MESSAGES_lang)
  MESSAGES.update({lang:{'messages':{}}})
  new_msg = list(translator.translate(list(MESSAGES_en.values()), dest=lang))
  for i, k in enumerate(MESSAGES_en.keys()):
    if type(new_msg[i]) is list:
      for msg in new_msg[i]:
        MESSAGES[lang]["messages"].update({k: msg.text})
      continue
    MESSAGES[lang]["messages"].update({k: new_msg[i].text})
#  p(MESSAGES[lang])
  new_msg = translator.translate(list(intents_en), dest=lang)
  intents.update({lang:{'messages':[]}})
  msg_arr, i = [], 0
  for dict_ in intents['en']['messages']:
    resp, msg = [], {}
    for k, v in dict_.items():
      if k == 'tag' or k == 'patterns':
        msg.update({k: v})
        continue
      for j in range(len(intents['en']["messages"][i]["responses"])):
        resp.append(new_msg[i][j].text)
    msg.update({"responses": resp})
    msg_arr.append(msg)
    i += 1
  intents[lang].update({"messages": msg_arr})
  # save the new langauge
  new_d = {"intents": {"language": {lang: {'messages': {}}}},
          "messages": {"language": {lang: {'messages': {}}}}}
  new_d['intents']['language'][lang] = intents[lang]
  new_d['messages']['language'][lang] = MESSAGES[lang]
  # read old new langaused that were not yet added to main messages file
  list_d = []
  try:
    with open(path + 'new_messages.json', "r") as f:
      list_d = json.loads(f.read())
  except:# Exception as error:
    pass
    #p(error)
  list_d.insert(0, new_d) #append(new_d)
  #p(list_d)
  with open(path + 'new_messages.json', "w") as f:
    json.dump(list_d, f, indent=1, ensure_ascii = False)
  send_email(f"New language added: {lang}", 'New language')

#p(translator.detect('الشغل'))
# 'xab' is in Hmong langauge (hmn)
#p(translator.detect('Работа'))
#add_language('iw') # hebrew
#add_language('ar') # arabic
#add_language('ru') # russian

def is_valid_date_p(dt):
    if dt:
        try:
            dt = dt.translate(space_punct_dict)
            new_date = str(parse(dt, fuzzy=True))[:10]
            year = int(new_date[:4])
            month = int(new_date[5:7])
            day = int(new_date[8:])
            ndays = (date(year, month, day) - date.today()).days
            return True, year, month, day, ndays
        except:
            p('invalid:', dt)
            return False, None, None, None, None
    return False

def run_bot(user_msg, VERBOSE=0, LANG='en', new_lang='', org_msg=''):
    do = True
    NOANSWER = 3
    min_similarity = 0.84
    DEBUG = VERBOSE
    error = ''

    while do:
      #user_msg = input().lower().strip()
      if user_msg == '':
        answers = intents[LANG]["messages"][NOANSWER]['responses']
        return '', random.choice(answers), False, LANG, '', '', ''

      if new_lang != '':
        if user_msg == '1':
          if new_lang not in MESSAGES_lang or new_lang=='fr':
            add_language(new_lang)
          LANG = new_lang
        user_msg = org_msg
        new_lang = ''
      else:
          response = translator.detect(user_msg)
          if response.lang == 'iw': response.lang = 'he'
          if response.lang != LANG:
              p(response.lang)
              if response.lang in ['en','he']:
                LANG = response.lang
              else:
                verify = True
                if response.lang not in MESSAGES_lang:
                    # add langauge only when sure - of at least 3 words of length 5 letters each - to prevent erroneous detection
                  sentence = ' '.join(filter(None, user_msg.split(' ')))
                  if not (len(sentence) > 11 and len(user_msg.split()) > 2):
                    verify = False  # False "new langauge" - google think that 'haifa israel' is in arabic, and 'Paris, frnace' is in french
                if verify:
                  new_lang = response.lang
                  answer = MESSAGES[LANG]["messages"]["new_lang"].format(new_lang)
                  return user_msg, answer, False, LANG, new_lang, '', ''
          elif LANG == 'en': # check if the google translate stopped working
              test = translator.detect('שלום וברכה')
              if test.lang == LANG:
                error = 'Note: Google translate stopped working temporarily -> multi-lingual option is not functional'
                p(error)

      round = 0
      answer = ''
      org_msg = user_msg
      tag, url_icon = '', ''
      while round < 4 and do:
        if VERBOSE:   p(f'round {round}: {user_msg}')
        doc1 = nlp(user_msg)
        answers, tag = None, None
        top_similarity = 0
        # verify not an erroeous finding (if we have GPE in the doc we assume it is not a general request)
        if len([ent for ent in doc1.ents if ent.label_ == 'GPE']) == 0:
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
          if top_similarity > min_similarity:
            if tag == "goodbye":
              do = False
            if tag in ["goodbye", "greeting", "thanks", "options"]:
              answer = random.choice(answers)
              break
#        if round == 2 and session['google']: round = 3 # to know we got the answer from get_parts()
        parts = get_parts(user_msg, DEBUG, LANG, VERBOSE > 1, False)
        if VERBOSE:  p(parts)
        if 'date' in parts and 'city' in parts and 'ERROR' not in parts['city'][0][1]:
          #p(parts['city'])
          answer, url_icon = get_weather(parts['date'], parts['city'], parts['action'], LANG)
          break
        elif 'city' in parts and 'ERROR' in parts['city'][0][1]:
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
          user_msg = translator.translate(org_msg) # default translation is to english - can set source/dest langauge: src="de"/ dest="he"
          if VERBOSE:  p(f"{user_msg.origin} ({user_msg.src}) --> {user_msg.text} ({user_msg.dest})")
          user_msg = user_msg.text
          if user_msg != '':
            continue
        if round == 2:
          round = 3
          user_msg = get_google(org_msg)
          if user_msg != '':
            continue
        break
      if answer == '':  answer = MESSAGES[LANG]["messages"]["city_unknown"]
      else:
        #p('round: ', round, (round >= 2 and not 'ERROR' in answer))
        if round >= 2 and not 'ERROR' in answer and session['google']:
          answer += f' ({MESSAGES[LANG]["messages"]["from_google"]})'

      return org_msg, answer, tag=="goodbye", LANG, '', error, url_icon


