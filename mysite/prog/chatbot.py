#echo > /var/log/drbarak.pythonanywhere.com.error.log

from flask import render_template, redirect, request, session
from flask_app import app

from prog.forms import ChatForm

import spacy, random, requests, bs4, time
import pandas as pd

from prog.chatbot_init import nlp, stopwords, remove_punct_dict, api_key, URL, translator
from prog.chatbot_init import df_CITIES_API, CITIES_API_country_code
from prog.chatbot_init import countries_df
from prog.chatbot_init import cities_il_df, CITIES_IL
from prog.chatbot_init import capitals_df, CAPITALS
from prog.chatbot_init import largest_df
from prog.chatbot_init import intents

from globals import Globals

globals = Globals()

def p(msg=None, *args):
    try:
        if msg is None:
            app.logger.warning('')
            return
    except: # if there is an error (eg. msg is a DataFrame (on some version of pyhton) can not test for None)
        pass  # if the is an excpetion we know it is not None
    msg = f'{msg}'
    for k in args:
        msg = msg + f' {k}'
    app.logger.warning(msg)

IDLE_TIME = 60 * 30 # max half an hour between questions to the bot

def chatbot():
    if 'chat_' not in session:
        p('in chatbot', spacy.__version__)
        session['chat_'] = 'chat_'
        session['username_'] = 'admin_'
        session['df_chat'] = []
        session['time'] = time.time()
        session['google'] = False
        session['index'] = 1
        session['clear'] = False
        session['debug'] = 0
    else:
        if 'google' not in session:
            session['google'] = False
        if 'clear' not in session:
            session['clear'] = False
        if not 'debug' in session:
            session['debug'] = 0
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
    df_chat = pd.DataFrame(session['df_chat'], columns=['index', 'ID', 'Conversation'])
    form = ChatForm()
    error = ''
    if request.method == 'POST':
        if form.run_bot.data:
            user_msg, answer, goodbye = run_bot(form.user_msg.data)
            #error = answer
            if session['clear']:
                session['index'] = 1
                session['df_chat'] = []
                session['clear'] = False
            index = session['index']
            session['df_chat'] = [[index + 1, 'Bot: ', answer], [index, 'You: ', user_msg]] + session['df_chat']
            df_chat = pd.DataFrame(session['df_chat'], columns=['index', 'ID', 'Conversation'])
            session['index'] = index + 2
            if goodbye == True:
                session['clear'] = True # clear the log after displaying this message
            return redirect('/chatbot')  # to clear the form fields
        if form.google.data:
            session['google'] = False if session['google'] else True
        if form.debug.data:
            session['debug'] = 0 if session['debug'] else 2
    #df_chat_html = df_chat.style.applymap(lambda attr: 'font-weight: bold;', subset=['index'])
    df_chat_html = (df_chat.style
                        .set_properties(subset=['index'], **{'font-weight': 'bold'})
                        .set_properties(subset=['Conversation'], **{'width': '500px'})
                        .set_properties(subset=['index'], **{'width': '20px'})
                        .hide_index()
                        .render()
                        .replace('index','')
                        )
    return render_template('chatbot.html', title='CHAT BOT', form=form, error=error, df_chat=df_chat_html, length=len(df_chat))

WEATHER_ONLY = 1

def call_web(city_name, country, count=1):
    state = ''
    api_url = f"{URL}q={city_name},{state},{country}&cnt={count}&appid={api_key}"
    #p(api_url)

    response = requests.get(api_url)
    response_dict = response.json()

    weather = response_dict #["weather"]#[0]#["description"]

    if response.status_code == 200:
        return weather
    elif response.status_code == 404:
        return None
    else:
        print('[!] HTTP {0} calling [{1}]'.format(response.status_code, api_url))
        return None

def get_weather(dt, location, action = None):
  template = WEATHER_ONLY

  city_w = city = location[0][0]  # assume one city (not handling ifthere are 2 cities)
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

  #p(city_w)
  country = location[0][1]
  p(country)
  p('0:')
  p(countries_df.Name)
  p('1:')
  p(list(countries_df.Name))
  p('2:')
  p(countries_df[countries_df.Name == country])
  if country in list(countries_df.Name):
    country_code = countries_df[countries_df.Name == country].index[0]
  else:
    country_code = ''

  city_weather = call_web(city_w, country_code)
  if city_weather is not None:
    if template == WEATHER_ONLY:
      result = city_weather["weather"][0]["description"]
    return f"In {city.capitalize()}, {location[0][1].capitalize()} the current weather is: {result}"
  else:
    return "Something went wrong."

#answer = get_weather('current', [('toronto', 'united states')])
#answer
"""# Get Parts (POS)"""


DEBUG = False
def get_parts(text, disp=False, verbose=True):
  doc = nlp(text.lower().translate(remove_punct_dict))
  date, gpe, ents = [], {}, []
  action = ''
  multiple_cities = False
  if disp: p()
  for token in doc:
    if disp:
      p(f'{token.text}, dep_={token.dep_}, ent_type={token.ent_type_}, head={token.head}, lemma_={token.lemma_}, pos_={token.pos_}, tag_={token.tag_}')
    if token.ent_type_ == 'GPE': ents.append((token.text.lower(), token))
  for entity in doc.ents:
      if disp:
        print(f"{entity.text}, {entity.label_}='{spacy.explain(entity.label_)}', is_city={entity._.is_city}, is_country={entity._.is_country}")
      ent_text = entity.text.lower().translate(remove_punct_dict)
      if entity.label_ == 'DATE': date.append(ent_text)
      if entity.label_ == 'GPE':
        token = None
        for e in ents:
          if ent_text == e[0]:
            token = e[1]
            break
        # verify the GPE is a true GPE for cases that a city has a name that has another meaninig
        if token and token.text != token.lemma_: # a true GPE cannot be lemmatized
          continue
        # for example there is a city in Denemark that has a name 'rain'
        if token and len(ents) > 1 and (token.head == token or token.pos_ not in ['PROPN', 'PRON', 'NOUN']) and not entity._.is_country:
          valid_gpe = False
          for e in ents:
            if ent_text != e[0]:
              tk = e[1]
              if tk.head == token:  # the token is connected to another gpe, so it is a valid gpe (for example, (paris, canada) are connected
                valid_gpe = True
                break
          if not valid_gpe:
            if DEBUG: p('A:', ent_text)
            continue
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
              #ent_country = countries_df.loc[code_country[0]].Name
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
  if len(date) == 0:
    date = 'current'

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
            gpe['city'] = (gpe['city'][j][0], city_country)
            gpe['country'] = city_country
            check_capital = False
            break
      if check_capital:
        # check if one of the cities is a capital or a large city, then use it
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
        gpe['city'] = [(city, f'ERROR: city [{city}] not found in country [{country}] - try a different spelling of the city')]
  elif 'country' in gpe and 'city' not in gpe:  # country without city, get the capital
    country = gpe['country'][0]
    if country in CAPITALS:
      gpe['city'] = [(CAPITALS[country], country)]
  result = {}
  result['date'] = date
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

def run_bot(user_msg, VERBOSE = 0):
    do = True
    NOANSWER = 3
    #p(intents['intents'][GREETING]['responses'][0])
    min_similarity = 0.84

    while do:
      #user_msg = input().lower().strip()
      if user_msg == '':
        answers = intents['intents'][NOANSWER]['responses']
        return '', random.choice(answers), False

      round = 0
      answer = ''
      org_msg = user_msg
      tag = ''
      while round < 5 and do:
        if VERBOSE:   p(f'round {round}: {user_msg}')
        doc1 = nlp(user_msg)
        answers, tag = None, None
        top_similarity = 0
        # verify not an erroeous finding (if we have GPE in the doc we assume it is not a general request)
        if len([ent for ent in doc1.ents if ent.label_ == 'GPE']) == 0:
          for ints in intents['intents']:
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
        if round == 2 and session['google']: round = 3 # to know we got the answer from get_parts()
        parts = get_parts(user_msg, VERBOSE > 1, False)
        if VERBOSE:  p(parts)
        if 'date' in parts and 'city' in parts and 'ERROR' not in parts['city'][0][1]:
          #p(parts['city'][0][0])
          answer = get_weather(parts['date'], parts['city'], action=None)
        elif 'city' in parts and 'ERROR' in parts['city'][0][1]:
          answer = parts['city'][0][1]
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
          user_msg = get_google(org_msg)
          if user_msg != '':
            continue
        if round == 2 or round == 3:
          round = 4
          user_msg = translator.translate(org_msg) # deafaul translation is to english - can set source/dest langauge: src="de"/ dest="he"
          if VERBOSE:  p(f"{user_msg.origin} ({user_msg.src}) --> {user_msg.text} ({user_msg.dest})")
          user_msg = user_msg.text
          if user_msg != '':
            continue
        p('round: ', round)
        if round >= 3 and not answer == '' and not 'ERROR' in answer:
          answer += ' (from Google)'
        break
      if answer == '': answer = "You need to tell me a city to check (maybe spell it differently)"
      return org_msg, answer, tag == "goodbye"