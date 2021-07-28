from flask_app import db, GameDB
import csv

from prog.chatbot_init import p
import pickle

movies = {}
def load_movies():
    #global movies
    #static_dir_prefix = "./static"
    static_dir_prefix = '/home/drbarak/mysite/static'

    movies_dir = '/movies/'
    posters_dir = '/posters/'
    movie_type = '.mp4'
    poster_type = '.jpg'
    movie_list_file = 'movies.csv'

    with open(static_dir_prefix + movies_dir + movie_list_file) as movies_file:
        for line in csv.reader(movies_file):
            level, question_number, clip_file, correct_answer = line
            if int(level) not in movies:
                movies[int(level)] = {}
            movies[int(level)][int(question_number)] = {
                "video_source": movies_dir + clip_file + movie_type,
                "poster_source": posters_dir + clip_file + poster_type,
                "correct_answer": int(correct_answer)
            }

def read_from_db():
  n = -1
  #p(f'in read_from_db [{n}], [{text}]')
  row = GameDB.query.get(n)
  #p(f'in read_from_db_1: [{row}]')
  if row is None or row.db_chat is None:
    return {}, 0
  df_chat = pickle.loads(row.db_chat)
  return df_chat, len(df_chat)

def game_init():
    load_movies()
    #return
    # game_init is called each time flask_app.py is run so we can not do session.commit because it closes the session and then can not do db operation in game.py
    # we need to call it once, to create the only record -1 and afterwards rely on clear_games() to clear old games
    # therefore active_players is not the len(games) and we need to keep track of it seperately
    n = -1
    #row = read_from_db()
    row = GameDB.query.get(n)
    #p('in game_init', row)
    if row is None:
      row = GameDB(id=n, db_chat=None)
      db.session.add(row)
      p(f'add new record [{n}]')
      db.session.commit()
    else:
      row = GameDB.query.get(n)
      row.db_chat = None
      db.session.commit()
      p('clear db', n)