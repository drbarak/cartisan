# echo > /var/log/drbarak.pythonanywhere.com.error.log

from flask import render_template, redirect, request
from flask_app import session

from prog.forms import ChatForm

import spacy, random, requests, bs4, time, json
import pandas as pd

from prog.chatbot_init import nlp, stopwords, remove_punct_dict, path
from prog.chatbot_init import QUESTIONS
from prog.chatbot_init import MESSAGES_lang, MESSAGES, MESSAGES_en, intents, intents_en
from prog.chatbot_init import p, send_email, NO_DAYS
from prog.chatbot_init import googletrans_api, translator, google_translate, google_detect

from prog.chatbot_parts import get_parts
from prog.chatbot_dates import check_date
from prog.chatbot_web import get_weather

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
                p('clear df_chat', delta > IDLE_TIME, session['index'] == 0)
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

def var_value(**var):  p(var)
'''
    var_value(RUN_TEST=RUN_TEST)
    var_value(LANG=LANG)
    var_value(switched_lang = switched_lang)
    var_value(YES_NO = YES_NO)
    var_value(yes_addition = yes_addition)
    var_value(QUESTIONS=QUESTIONS)
    var_value(QUESTIONS_LANG = QUESTIONS[LANG])
    var_value(QUESTIONS_LANG_0 = QUESTIONS[LANG][0])
'''

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
        if user_msg in responses_yes or user_msg in intents[new_lang]["messages"][YES]['responses'] or google_translate(user_msg) in responses_yes:
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
                  answer = MESSAGES[LANG]["messages"]["new_lang"].format(new_lang.upper()) + "<br>"
                  if new_lang in MESSAGES_lang:
                    answer += MESSAGES[new_lang]["messages"]["new_lang"].format(new_lang.upper())
                  else:
                    answer += google_translate(MESSAGES['en']["messages"]["new_lang"]).format(new_lang.upper())
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
        if user_msg in responses_yes or (new_lang != '' and user_msg in intents[new_lang]["messages"][YES]['responses']) or google_translate(user_msg) in responses_yes:
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
            parts = get_parts(user_msg.lower(), LANG, VERBOSE > 0) # need to use lower() because google might return in capitalization
            if VERBOSE:  p('x:', parts, round, LANG, switched_lang)
            if len(parts.get('date')) > 0:
              israel = False
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
          import html
          user_msg = html.unescape(get_google(org_msg))
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
        if city != '':
          answer = MESSAGES[LANG]["messages"]["error_current"].format(answer, city, action, date)
          if date == '':
            date = "'Today'"
            if LANG != 'en': date = f"'{google_translate('Today', dest=LANG)}'"
          else: date =''
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


