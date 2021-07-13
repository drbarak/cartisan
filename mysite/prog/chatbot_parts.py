# echo > /var/log/drbarak.pythonanywhere.com.error.log

import spacy

import pandas as pd

from prog.chatbot_init import nlp, stopwords, remove_punct_dict
from prog.chatbot_init import df_CITIES_API, CITIES_API_country_code
from prog.chatbot_init import largest_df, countries_df
from prog.chatbot_init import capitals_df, CAPITALS
from prog.chatbot_init import ACTIONS#, ACTIONS_patterns, ACTIONS_tags
from prog.chatbot_init import MESSAGES
from prog.chatbot_init import p
from prog.chatbot_init import dayInWeek, dateToNum, dates_str

from prog.chatbot_dates import is_valid_date

def check_gpe(entity, ents, ent_text, gpe, multiple_cities, disp):
  if disp: p('in check_gpe', ent_text, gpe, ents)
  token = None
  for e in ents:
    if ent_text == e[0]:
      token = e[1]
      break
  # verify the GPE is a true GPE for cases that a city has a name that has another meaninig
  if token and token.text != token.lemma_: # a true GPE cannot be lemmatized
    #p(0, 'check_gpe', token.text, token.lemma_, token.text != token.lemma_)
    return 'continue', gpe, 0

  # for example there is a city in Denemark that has a name 'rain'
  if token and len(ents) > 1 and (token.head == token or token.pos_ not in ['PROPN', 'PRON', 'NOUN']) and not entity._.is_country and not entity._.is_city:
    valid_gpe = False
    for e in ents:
      if ent_text != e[0]:
        tk = e[1]
        if tk.head == token:  # the token is connected to another gpe, so it is a valid gpe (for example, (paris, canada) are connected
          valid_gpe = True
          break
#                return 'break', gpe, 0
    if not valid_gpe:
      #if disp: p('-:', ent_text, ents, entity._.is_city)
      return 'continue', gpe, 0

    # ignore city which is also a weather action, if it is the only action
  if token and token._.is_action and entity._.is_city and len(gpe['action']) == 1 and entity.text == gpe['action'][0][1]: # snow is a city and an action/ also rain
    return 'continue', gpe, 0

  ent_type = 'state'
  #if disp: p('0:', ent_text, entity._.is_city, entity._.is_country)
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
    city = gpe.get('city', '')
    #p('city', city, len(city),  (entity.text, ent_country) not in city)
    if len(city) == 0 or (entity.text, ent_country, token) not in city:
      gpe[ent_type].append((entity.text, ent_country, token))
  else:
    gpe[ent_type].append(entity.text)
  return None, gpe, multiple_cities

def get_city_country(multiple_cities, gpe, disp, LANG):
  if disp: p('in get_city_country', multiple_cities, gpe)
  token = None

  if 'country' in gpe and len(gpe.get('city', '')) > 0:  # added 12.07.2021: to eliminate cities that have same name as action that are not in the same country (or no multiple cities so it for sure wrong city)
    gpe_org = gpe['city'].copy()
    j = 0
    for i, (city, city_country, token) in enumerate(gpe_org):
      country = gpe['country'][0]
      if city_country != country and (token._.is_action or not multiple_cities):
        gpe['city'].pop(j)
        continue
      j += 1
    if len(gpe.get('city', '')) == 0:
      gpe.pop('city')

  if multiple_cities or ('city' in gpe and len(gpe['city']) > 1):
    if 'country' in gpe:
      # verify country code of the city is correct, when there are multiple cities, because we might have put the wrong country
      gpe_org = gpe['city'].copy()
      j = 0
      for i, (city, city_country, token) in enumerate(gpe_org):
        country = gpe['country'][0]
        if city_country != country:
          code_country = df_CITIES_API.loc[city].country
          if type(code_country) == str: # drop the wrong city
            '''
            # we drop the city 'of' from the database
            if (city, country) == ('of', 'israel'):
              gpe['city'].pop(j)
              continue
            '''
            gpe['city'].pop(j)
            continue
          else:
            found = False
            for code_country in df_CITIES_API.loc[city].country:
              if country == countries_df.loc[code_country].Name:
                # found a matching country
                gpe['city'][j] = (city, country, token)
                found = True
                '''
                if (city, country) == ('of', 'israel'): gpe['city'].pop(j)
                  break
                '''
                break
            if not found: # drop the wrong city
              gpe['city'].pop(j)
              continue
        j += 1
      if len(gpe['city']) == 0: # removed all cities
        gpe['city'] = [(city, "ERROR: " + MESSAGES[LANG]["messages"]["city_error"].format(city, country), token)]
    else:
      check_capital = True
      if len(gpe['city']) == 2: # maybe entered a country which has city with that name (eg. Toronto, US = there is a city name 'us' in france and 'usa' in japan)
        # 'city': [('toronto', 'Canada'), ('us', 'france')]
        for i in range(1,-1,-1):
          city = gpe['city'][i][0].upper()
          if city in countries_df.index: #usually the 2nd "city" is the country
            city_country = countries_df.loc[city].Name
            if type(city_country) == pd.Series:
              city_country = city_country.iloc[0]
            j = 0 if i == 1 else 1
            gpe['city'] = [(gpe['city'][j][0], city_country, gpe['city'][j][2])]
            gpe['country'] = city_country
            check_capital = False
            break
      if check_capital:
        # check if one of the cities is a capital or a large city, then use it
        #gpe, multiple_cities)
        for i, (city, city_country, token) in enumerate(gpe['city']):
          p(city, city_country, token, city in capitals_df.index.values)
          if city in capitals_df.index.values:
            # found a matching country
            city_country = capitals_df.loc[city].country
            if type(city_country) == pd.Series:
              city_country = city_country.iloc[0]
            gpe['city'][i] = (city, city_country, token)
            break
          if city in largest_df.index.values:
            # found a matching country
            city_country = largest_df.loc[city].country
            gpe['city'][i] = (city, city_country, token)
            break
  elif 'country' in gpe and 'city' in gpe:  # country with city, verify correct
      if disp: p('2:', gpe)
      # verify country code of the city is correct, when user entered
      city, city_country, token = gpe['city'][0]
      country = gpe['country'][0]
      if city_country != country:
        gpe['city'] = [(city, "ERROR: " + MESSAGES[LANG]["messages"]["city_error"].format(city, country), token)]
  elif 'country' in gpe and 'city' not in gpe:  # country without city, get the capital
    country = gpe['country'][0]
    #country)
    if country in CAPITALS:
      gpe['city'] = [(CAPITALS[country], country, token)]
  return gpe, multiple_cities

def get_parts(text, LANG, disp=False):
  date, time, gpe, ents, ents_d = [], [], {'action':[]}, [], []
  multiple_cities = False
  round = 0
  while round < 2:
    doc = nlp(text)
    #doc = nlp(text.lower().translate(space_punct_dict))
    if disp: p()
    for token in doc:
      if disp: p(f"Tokens of [{token.text}]: dep_={token.dep_}, ent_type={token.ent_type_}, head={token.head}, lemma_={token.lemma_}, pos_={token.pos_}, tag_={token.tag_}, is_action={token._.is_action}")
      if token._.is_action:  # checking for action first catch cities with the same name ('rain' is a city)
        tag = ACTIONS[token.lemma_]
        tag_exists = [t for t in gpe['action'] if t[0] == tag]
        if len(tag_exists) == 0:
          gpe['action'].append((tag, token.lemma_))
        # on 12/07/2021 changed thenext line from 'elif' to 'if' to catch cities with the same name as action so can later eliminate it if needed (need the Toaken)
      if token.ent_type_ == 'GPE': ents.append((token.text, token))
      elif token.ent_type_ in ['DATE', 'TIME', 'CARDINAL']:
        # after google translate we removed punct so dates come as a single number 15/07/2021 -> 15/07/2021
        if token.text.isnumeric():
          if len(token.text) == 8 or len(token.text) == 6:
            text = token.text[:2] + ' ' + token.text[2:4] + ' ' + token.text[4:]
            date.append(text)
            ents_d.append((token.text, token, 'ignore'))
            continue
        ents_d.append((token.text, token, ''))
      elif token.text == 'country' and 'of the country' in text:
        gpe['country'] = ['israel']
      elif token.pos_ == 'NUM':
        if is_valid_date(token.text)[0]: date.append(token.text)
    for entity in doc.ents:
      if disp: p(f"Entities of [{entity.text}]: {entity.label_}='{spacy.explain(entity.label_)}', is_city={entity._.is_city}, is_country={entity._.is_country}")
      ent_text = entity.text.translate(remove_punct_dict)
      if entity.label_ in ['DATE', 'TIME', 'CARDINAL']:
        if len(ent_text.split()) > 1 and ent_text in dates_str: # do not touch reserved phrases (such as 'day after tomorrow)
          date.append(ent_text)
          continue
        if len(ent_text.split()) > 1: # take care of the case 'wednesady next week' without comma
          token = None
          for e in ents_d:
            if e[0] in ent_text:
              token = e[1]
              if token.text in dayInWeek or token.text in dateToNum: # a seperate entity
                if token.text not in date:
                  date.append(token.text)
              elif token.head.text in ['for'] and 'next' not in ent_text: # for 2 days = next 2 days
                ent_text = 'next ' + ent_text
              elif token.head.text in ['in'] and len(date) == 1 and 'one week' in ent_text: # in one (week) = deat date and not range so need to compbine with the days
                ent_text = date[0] + ' next ' + ent_text[4:]
              elif token.text == 'a':  # replace 'a week' with 'one week'
                idx = ent_text.find(token.text)
                ent_text = ent_text[:idx] + 'one' + ent_text[idx + 1:]
              elif e[2] == 'ignore': # taken care in Token round - see above
                ent_text = ''
                break
          idx0 = 0
          ent_t = ent_text
          for word in ent_t.split(): # take care of "July 10 for 3 days" without comma
            if word in stopwords:
              idx1 = ent_text.find(word)
              if idx1 < 0 :continue # not found
              if idx1 == 0: continue # first word of the sentence, so no need to treat as if no comma
              '''
              #p(word, idx1, ent_text)
              if idx1 == 0:
                ent_text = ent_text.replace(word, '').strip()
                p(ent_text)
                continue #  first word of the sentence, so no need to treat as if no comma
              #p(word, idx1, ent_text)
              '''
              if ent_text[idx0:idx1-1] not in date:
                #p('1-', ent_text[idx0:idx1-1])
                date.append(ent_text[idx0:idx1-1])
              idx0 = idx1 + len(word) + 1
              ent_t = ent_text[idx0:]
        elif ent_text == 'weekly':
          ent_text = 'this week'
          # if the text is 'in day after tomorrow in Moscow' compared to 'in Moscow the day after tomorrow' spacy will not recognize 'day after tomorrow' as phrase and break it to 2 entities 'day', 'tomorrow'
        elif ent_text in ['tomorrow']:
          if date == ['day']:
            date = ['the day after tomorrow']
            ent_text = ''
          # on 12.07.2021 commented the next line because we now allow multiple date expressions (on Tusaday for 3 days)
#        if len(ent_text.split()) == 1 or len(date) == 0:
        if ent_text!= '' and ent_text not in date:
            #p('2-', ent_text)
            date.append(ent_text)
      '''
      if entity._.is_action:  # 'rain' is both a city and weather action
        tag = ACTIONS[ent_text]
        gpe['action'].append((tag, ent_text))
      '''
      if entity.label_ == 'GPE' or (entity.label_ == 'PERSON' and entity._.is_city):
        #if disp: p('calling check_gpe', entity)
        act, gpe, multiple_cities = check_gpe(entity, ents, ent_text, gpe, multiple_cities, disp)
        if disp: p('after check_gpe', entity, act)
        if act == 'continue': continue
        if act == 'break': break
    gpe, multiple_cities = get_city_country(multiple_cities, gpe, disp, LANG)
      # remove city with same name as action ('rain') if there is another city (or how many degrees - three is a city in US named many)
    '''
        Tokens of [how]: dep_=advmod, ent_type=, head=many, lemma_=how, pos_=ADV, tag_=WRB, is_action=False
        Tokens of [many]: dep_=amod, ent_type=GPE, head=degrees, lemma_=many, pos_=ADJ, tag_=JJ, is_action=False
        Tokens of [degrees]: dep_=ROOT, ent_type=, head=degrees, lemma_=degree, pos_=NOUN, tag_=NNS, is_action=True
        Tokens of [in]: dep_=prep, ent_type=, head=degrees, lemma_=in, pos_=ADP, tag_=IN, is_action=False
        Tokens of [hadera]: dep_=compound, ent_type=GPE, head=ofakim, lemma_=hadera, pos_=PROPN, tag_=NNP, is_action=False
        Tokens of [ofakim]: dep_=pobj, ent_type=, head=in, lemma_=ofakim, pos_=PROPN, tag_=NNP, is_action=False
        Tokens of [in]: dep_=prep, ent_type=, head=degrees, lemma_=in, pos_=ADP, tag_=IN, is_action=False
        Tokens of [2]: dep_=nummod, ent_type=DATE, head=days, lemma_=2, pos_=NUM, tag_=CD, is_action=False
        Tokens of [days]: dep_=pobj, ent_type=DATE, head=in, lemma_=day, pos_=NOUN, tag_=NNS, is_action=False
          'action': [('temp', 'degree')]
    '''
    if 'city' in gpe:
      org_gpe = gpe['city'].copy() # copy because the list is modified inside the loop
      for tup in org_gpe:
        city = tup[0]
        city_exists = [t for t in gpe['action'] if t[0] == city or t[1] == city]
        if len(city_exists) == 0: # could be indirect name such as 'how many degrees:
          token = tup[2]
          if token:
            #p(token, token.head.lemma_, gpe['action'])
            city_exists = [t for t in gpe['action'] if t[1] == token.head.lemma_]
          if len(city_exists) == 0:
            continue
        if len(gpe['city']) == 1:  # must leave at least one city
          # remove from action list if appears only once in the sentence
          n = [t for t in doc if t.text == city]
          if len(n) > 1: continue
          # but must leave at least one action
          if len(gpe['action']) > 1:  gpe['action'].remove(city_exists[0])
          continue
        gpe['city'].remove(tup)

    if len(gpe['action']) > 0:
      #gpe['action'] = [('all', 'weather')]
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
    if 'city' not in result:
      p(f'FAILED: org [{text}], {result}')
  return result
