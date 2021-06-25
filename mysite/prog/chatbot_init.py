from flask_app import app

import pandas as pd

import nltk
import json, string
import spacy
from spacy.tokens import Span #Doc,
from spacy.matcher import PhraseMatcher
from spacy.language import Language
'''
to install spacy:
1. pip3.8 install spacy==2.2.4 --user
2. python3.8 -m spacy download en_core_web_md
'''
spacy.load('en_core_web_md')
import en_core_web_md

nlp = en_core_web_md.load()
nltk.download(['punkt', 'stopwords'])

#my_import('googletrans', version='3.1.0a0')
from googletrans import Translator
translator = Translator()

FAST_START = False

stopwords = nltk.corpus.stopwords.words('english')
remove_punct_dict = dict((ord(punct), None) for punct in string.punctuation)

api_key = 'c2adfa29edfd95ad16efab9218619ff3'
URL = "http://api.openweathermap.org/data/2.5/weather?"

path = '/home/drbarak/mysite/png/'

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

def init_chatbot():
    p('init chatbot')

"""# Get cities and update model"""

def get_json(fname):
#  p(fname)
  with open(path + fname, encoding="utf8") as f:
    return json.loads(f.read())
intents = get_json('intents.json')
#p(intents)

def load_CITIES_API():
  CITIES_API = get_json('city.list.json')

  df = pd.DataFrame(CITIES_API)
  df = df.drop(['id', 'coord'], axis='columns')
  df.name = df.name.str.lower()
  df.name = df.name.str.translate(remove_punct_dict)

  CITIES_API_city = sorted(set(df.name.to_list()))
  CITIES_API_country = sorted(set(df.country.str.lower().to_list()))
  if CITIES_API_country[0] == '':
    CITIES_API_country = CITIES_API_country[1:]
  CITIES_API_state = sorted(set(df.state.str.lower().to_list()))
  if CITIES_API_state[0] == '':
    CITIES_API_state = CITIES_API_state[1:]
  if CITIES_API_state[0] == '00':
    CITIES_API_state = CITIES_API_state[1:]

  df.set_index('name', inplace=True)
  #d(df.head)
  return df, CITIES_API_city, CITIES_API_country, CITIES_API_state
df_CITIES_API, CITIES_API_city, CITIES_API_country_code, CITIES_API_state_code = load_CITIES_API()
#p(df_CITIES_API.head())

def load_countries():
  fname = 'countries.csv'
  df = pd.read_csv(path + fname)
  df.Name = df.Name.str.lower()
  COUNTRIES = df.Name.tolist()
  df = df.set_index('Code')
  return df, COUNTRIES
countries_df, COUNTRIES = load_countries()
#p(countries_df.head())

def load_cities_il():
  fname = 'cities_IL.csv'
  df = pd.read_csv(path + fname, names=['city', 'district'])
  df.city = df.city.str.translate(remove_punct_dict)
  CITIES = df.city.tolist()
  df = df.set_index('city')
  return df, CITIES
cities_il_df, CITIES_IL = load_cities_il()
#p(cities_il_df.head())

def load_capitals():
  fname = 'capitals.json'
  CAPITALS = pd.read_json(path + fname, encoding="utf8", typ='series').str.lower()

  CAPITALS.index = CAPITALS.index.str.lower()
  df = pd.DataFrame([CAPITALS])
  df = df.T
  df = df.reset_index()
  df.columns = ['country', 'capital']
  df = df.set_index('capital')
  return df, CAPITALS.to_dict()
capitals_df, CAPITALS = load_capitals()
#p(CAPITALS['albania'])
#p(capitals_df.loc['madrid'].country)
#capitals_df.head()

def load_largest():
  fname = '100-largest-cities.csv'
  df = pd.read_csv(path + fname, encoding='ISO-8859-8')
  df.city = df.city.str.lower()
  df.city = df.city.str.translate(remove_punct_dict)
  LARGEST = df.city.tolist()
  df = df.set_index('city')
  return df, LARGEST
largest_df, LARGEST = load_largest()
#p(largest_df.head())
#p(largest_df.loc['toronto'].country)

def update_nlp():
  matcher = PhraseMatcher(nlp.vocab)
  CITIES = set(CITIES_IL + CITIES_API_city)

  # disable other pipes while doing the traing to speed it up - went down from 1:40 to 0:40 minutes
  if not FAST_START:
      other_pipes = [pipe for pipe in nlp.pipe_names if pipe != 'ner']
      with nlp.disable_pipes(*other_pipes):
        matcher.add("CITIES", None, *list(nlp.pipe(CITIES)))

  # country codes causes problems because many are similar to regular words (eg. 'IN' similar to 'in')
  #matcher.add("CITIES_API_country_code", None, *list(nlp.pipe(CITIES_API_country_code)))
  # due to duplicates with country codes ('IL' = Israel, and Ilinoie), we have to check manually for states
  #matcher.add("CITIES_API_state_code", None, *list(nlp.pipe(CITIES_API_state_code)))

  # Register the Span extension attributes "is_country" and "is_city"
  check_country = lambda span: span.text.lower().translate(remove_punct_dict) in COUNTRIES
  Span.set_extension('is_country', getter=check_country, force=True)

  check_city = lambda span: span.text.lower().translate(remove_punct_dict) in CITIES
  Span.set_extension('is_city', getter=check_city, force=True)

  pipes = nlp.pipe_names
  if 'gpe_component' in pipes:
    nlp.remove_pipe('gpe_component')

  if spacy.__version__ > '3':
    @Language.component("gpe_component")
    def gpe_component(doc):
        # Create an entity Span with the label "GPE" for all matches
        matches = matcher(doc)
        try:
          doc.ents = [Span(doc, start, end, label="GPE") for match_id, start, end in matches]
        except ValueError as e: #[E103] Trying to set conflicting doc.ents: '(2, 4, 'GPE')' and '(3, 4, 'GPE')'. A token can only be part of one entity, so make sure the entities you're setting don't overlap.
          if 'E103' in e.args[0]:
            return doc  # use the standard model of Spacy, hopefully it works (as in the case "weather in new york") or  other rounds will get the proper result
          raise
        return doc

    # Add the new component to the pipeline
    nlp.add_pipe('gpe_component', first=True)
  else:
    def gpe_component(doc):
        # Create an entity Span with the label "GPE" for all matches
        matches = matcher(doc)
        try:
          doc.ents = [Span(doc, start, end, label="GPE") for match_id, start, end in matches]
        except ValueError as e: #[E103] Trying to set conflicting doc.ents: '(2, 4, 'GPE')' and '(3, 4, 'GPE')'. A token can only be part of one entity, so make sure the entities you're setting don't overlap.
          if 'E103' in e.args[0]:
            return doc  # use the standard model of Spacy, hopefully it works (as in the case "weather in new york") or  other rounds will get the proper result
          raise
        return doc

    # Add the new component to the pipeline
    nlp.add_pipe(gpe_component, first=True)

  #p(nlp.pipe_names)

update_nlp()

