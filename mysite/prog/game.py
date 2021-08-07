# echo > /var/log/drbarak.pythonanywhere.com.error.log

from flask import render_template, request, session
from dataclasses import dataclass, field
import random, time, sys, json

from prog.chatbot_init import send_email

def p(msg=None, *args):
    try:
        if msg is None:
            print('', file=sys.stderr, flush=True)
            return
    except: # if there is an error (eg. msg is a DataFrame (on some version of pyhton) can not test for None)
        pass  # if the is an excpetion we know it is not None
    msg = f'{msg}'
    for k in args:
        msg = msg + f' {k}'
    print(msg, file=sys.stderr, flush=True)
    '''
    import datetime
    log, _ = read_from_db(True, n=-2)
    if 'log' not in log:
        log['log'] = ''
    log['log'] += f'<br>{datetime.datetime.now()}: {msg}'
    update_db(log, 0, n=-2)
    '''

GAME_DB = True
if GAME_DB:
    from flask_app import db, GameDB
    import pickle, csv

    def read_from_db(lock=False, n=-1):
      db.engine.connect()
      #p(f'in read_from_db [{n}], [{text}]')
      row = GameDB.query.get(n)
      #p(f'in read_from_db_1: [{row}]')
      if row is None:
        row = GameDB(id=n, db_chat=None)
        db.session.add(row)
        db.session.commit()
        #db.engine.connect()
      if row is None or row.db_chat is None:
        db.session.close()  # unlock the record
        #db.engine.connect()
        return {-1:0}, 0
      if not lock:
        db.session.close()  # unlock the record
        #db.engine.connect()
      df_chat = pickle.loads(row.db_chat)
      return df_chat, df_chat[-1]

    def update_db(df, active_games, n=-1):
      row = GameDB.query.get(n)
      #p('in update_db', n)
      df[-1] = active_games
      row.db_chat = pickle.dumps(df)
      db.session.commit()  # after the commit the session is closed so in order to do another db action need to re-connect (see flask_app.py) db = SQLAlchemy(app);db.engine.connect() - NO NEED: we move the connect just before read so we are always connected when reading
      #db.engine.connect()
      return

else:
    games = {}
    active_games = 0

movies = {}
max_level = 0
static_dir_prefix = '/home/drbarak/mysite/static'
def load_movies():
    global movies, max_level
    #static_dir_prefix = "./static"

    movies_dir = '/movies/'
    posters_dir = '/posters/'
    movie_type = '.mp4'
    poster_type = '.jpg'
    movie_list_file = 'movies.csv'

#        df = pd.read_csv(path + static_dir_prefix + movies_dir + movie_list_file, names=['level', 'question_number', 'clip_file', 'correct_answer'])
    with open(static_dir_prefix + movies_dir + movie_list_file) as movies_file:
        for line in csv.reader(movies_file):
            #p('in movies', line)
            level, question_number, clip_file, correct_answer = line
            level = int(level)
            #p('in movies', line, level)
            if level not in movies:
                movies[level] = {}
            movies[level][int(question_number)] = {
                "video_source": movies_dir + clip_file + movie_type,
                "poster_source": posters_dir + clip_file + poster_type,
                "correct_answer": int(correct_answer)
            }
    max_level = max(list(movies.keys()))

question_delay = 15  # seconds for each question until time is up
answer_delay = 3  # seconds to remain in screen after showing each answer
comm_delay = 10  # maximum communication delay allowed before moving to next question
max_time_to_start = 60 * 30 # max half an hour to start a game
RANDOM = True   # pickup questions randomly and not sequentially

LANG = ''
title,  MESSAGES_lang, MESSAGES = '', '', ''

import pusher

pusher_client = pusher.Pusher(
  app_id='1243958',
  key='370ad2f2bb3b0c02b4a8',
  secret='4c2ab71c7eede080aba4',
  cluster='ap2',
  ssl=True
)

def get_json(fname):
  with open(static_dir_prefix + fname, encoding="utf8") as f:
    return json.loads(f.read())

def load_messages():
  fname = 'messages.json'
  messages = get_json(fname)
  MESSAGES = {lang: messages["messages"]["language"][lang] for lang in messages["messages"]["language"]}
  MESSAGES_lang = list(MESSAGES.keys())
  return MESSAGES_lang, MESSAGES

def my_render_template(path, *args, **kargs):
  html = render_template(path, **kargs)
  rtl = 'rtl' if LANG in ['he', 'iw', 'ar'] else ''
  return html.replace('<html',f'<html dir="{rtl}" lang="{LANG}"')

def init_game():
    global LANG, title, MESSAGES_lang, MESSAGES
    if max_level == 0:
        load_movies()
    if LANG == '':
        lang = request.args.get('lang')
        if lang is None:
          lang = LANG # remember last choice
        LANG = 'en' if lang is None else lang
        MESSAGES_lang, MESSAGES = load_messages()
        title = MESSAGES[LANG]["messages"]["title"]
    msg = f'in game_init {max_level}'
    p(msg)

'''
TODO:
1. SOLVED: handle game.end which reduce number of active games without deleting the game from the games{} and when clearing game not remove a game that ended. SOLVED: updating the db after game.end()
2. what url is in 'summary.html' href='home' - no direct in app.py - I changed to 'game' = the start screen
3. SOLVED: why do we need the 'wait_for_joining'? caused lose of global - worked 10 hours until I gave up and eliminated it all together - SOLVED: to know if another game was started or if somebody joined the game meanwhile
4. SOLVED: When creating a game it shows intially 1 player but then changes to 0. Why? - SOLVED: needed to update db after adding the player
5. DONE: to do show_summary() from show_question()
'''

# remove old games if overall time allocated for their questions (+1 for summary screen) is due
def clear_games(games, active_games):
    #global games#, question_delay, answer_delay, comm_delay
    p('in clear_games', request.headers['X-Real-IP'], games)
    for game in list(games):
        if game == -1: continue  # skip active_games field
        # games that did not started yet, we do not delete
        delta = int(time.time() -games[game].start_time())
        max_time_for_game = sum([question_delay, answer_delay, comm_delay]) * (games[game].total_questions()+1)
        if (games[game].game_is_on and delta > max_time_for_game) or (not games[game].game_is_on and delta > max_time_to_start):
            p('in clear_games', games[game].game_is_on, int(time.time() - games[game].start_time()), int(time.time()), int(games[game].start_time()), int(games[game].game_start_time), sum([question_delay, answer_delay, comm_delay]) * (games[game].total_questions()+1))
            games.pop(game)
            p('pop', game, games)
    if len(games) <= 1:
        active_games = 0
        games = {-1: 0}
    else:
        p('in clear_games', games, active_games)
    return games, active_games

#app = Flask(__name__, static_folder='static')

#@app.route('/')
def home(msg = ''):
    if 'game_' not in session:
        session['game_'] = 'game_'
        session['username_'] = 'admin_'
        session['time'] = time.time()
        session['game_code'] = 0
        session['player'] = 0
        session['lang'] = 'en'

        isMobile = any(ele in request.headers['User-Agent'] for ele in ['iPhone', 'iPad', 'iPod', 'Android'])
        session["mobile"] = '_mobile' if isMobile else ''

        if request.headers['X-Real-IP'] not in ['82.81.245.207', '50.17.220.95'] : # dr barak ip - no need to get a notice each time I log in
            send_email(text=msg, subject='Notice from Game', ip=request.headers['X-Real-IP'], src='Movie Quiz')
    else:
        if not 'game_code' in session:
            session['game_code'] = 0
            session['player'] = 0
        if not 'lang' in session:
            session['lang'] = 'en'


    if 'time' in session:
      session_time = session['time']
      delta = time.time() - session_time
      if delta > max_time_to_start:
        session['game_code'] = 0
        session['player'] = 0

    session['time'] = time.time()
    LANG = session['lang']

    #global active_games
    if GAME_DB:  games, active_games = read_from_db()  # do not clear_games, because players that want to join come here initally and created games but not started may pass the time alloted
    #p('in home', message, session["mobile"])
    if session["mobile"] == '':
        message = f"Games currently running: {active_games}{msg}"
        return render_template(f'game/home{session["mobile"]}.html', active_games=active_games, message=message, max_level=max_level)
    messages = MESSAGES[LANG]["messages"]["home"]
    messages[0] = f'{messages[0]} {active_games}'
    messages[3] = messages[3].format(max_level)
    return  my_render_template(f'game/home{session["mobile"]}.html', messages=messages, title=title, lang=LANG)


#@app.route('/help')
def help():
    '''
    log, _ = read_from_db(True, n=-2)
    send_email(text=log['log'], subject='Log from Game')
    log['log'] = ''
    update_db(log, 0, n=-2)
    '''
    return render_template('game/help_mobile.html')

#@app.route('/create_game/<int:level>')
def create_game(level):
    if level > max_level: level = max_level
    #p('in create_game', max_level, movies.keys())
    #global games, active_games
    if GAME_DB: games, active_games = read_from_db(True)
    valid_game_code = False
    while not valid_game_code:
        random.seed()
        game_code = random.randint(1000, 9999)
        valid_game_code = game_code not in games
    # before creating new games, take this opportunity to remove inactive ones
    games, active_games = clear_games(games, active_games)
    game = Game(game_level=level)
    games[game_code] = game
    session['game_code'] = game_code
    session['player'] = 1
    active_games += 1
    player = game.add_player()
    if GAME_DB: update_db(games, active_games)  # update and unlock the record
    #p('in create_game', game_code, games, active_games)
    return render_template(f'game/create_game{session["mobile"]}.html', game_code=game_code, player=player, players=game.number_of_players())

#@app.route('/start_game/<int:game_code>/<int:player>')
def start_game(game_code, player):
    #global games
    if GAME_DB: games, active_games = read_from_db(True)
    game = games[game_code]
    game.start()
    if GAME_DB:  update_db(games, active_games)
    p('in start_game', game_code, player, request.headers['X-Real-IP'], game.game_is_on, games, active_games)
    pusher_client.trigger(f'my-channel-{game_code}', 'my-event', {'tag': 'start', 'msg': f"player {player} joined game {game_code}"})
    return show_question(game_code=game_code, player=player)

#@app.route('/wait_for_joining/<int:game_code>/<int:player>')
def wait_for_joining(game_code, player):
    #global games
    #p('in wait_for_joining0:', game_code)
    if GAME_DB:   games, active_games = read_from_db()
    p('in wait_for_joining', game_code, active_games, player, request.headers['X-Real-IP'], games)
    if game_code not in games: # maybe time expired and was cleared in clear_games() by another user that logged in
        return home(f'Game code {game_code} not valid anymore - need to create a new game')
    game = games[game_code]
    return render_template(f'game/create_game{session["mobile"]}.html', game_code=game_code, player=player, players=game.number_of_players())

#@app.route('/join_game/')
def join_game():
    #global games
    if GAME_DB: games, active_games = read_from_db()
    if len(games) <= 1:
        game_code = 0
    else:
        game_code = list(games.keys())[0]
        if game_code == -1: game_code = list(games.keys())[1]
        p('in join_game1', game_code, list(games.keys()))
    return render_template(f'game/join_game{session["mobile"]}.html', game_code=game_code)

#@app.route('/join_validation/<int:game_code>')
def join_validation(game_code):
    #global games
    #p(f'in join_validation [{game_code}]')
    if GAME_DB: games, active_games = read_from_db(True)
    invalid = 0
    if game_code not in games:
        invalid = 1
    else:
        game = games[game_code]
        if game.is_on():
            invalid = 2
    if invalid:
        db.session.close()
        #db.engine.connect()
        message = 'Invalid game code' if invalid == 1 else 'Game already started!'
        return render_template(f'game/join_game{session["mobile"]}.html', game_code=game_code, message=message)
    game = games[game_code]
    new_player = True;
    if session['game_code'] == game_code: # prevent a user from doing refresh from his screen and thus causing to add him as a new user' loosing the previous one (this prevents multipple tabsqwindows from the same computer also)
        if session['player'] > 0:
            player = session['player']
            new_player = False;
        else:
            player = game.add_player()
    else:
        player = game.add_player()
    session['game_code'] = game_code
    session['player'] = player
    if GAME_DB: update_db(games, active_games)
    if new_player:
        pusher_client.trigger(f'my-channel-{game_code}', 'my-event', {'tag': 'player joined', 'msg': f"game {game_code} started"})
    #p(f"in join_validation [{f'my-channel-{game_code}'}]")
    return render_template(f'game/join_success{session["mobile"]}.html', game_code=game_code, player=player)

#@app.route('/wait_for_game_start/<int:game_code>/<int:player>')
def wait_for_game_start(game_code, player):
    #global games
    if GAME_DB: games, active_games = read_from_db()
    game = games[game_code]
    if game.is_on():
        return show_question(game_code=game_code, player=player)
    else:
        return render_template(f'game/join_success{session["mobile"]}.html', game_code=game_code, player=player)

#@app.route('/show_question/<int:game_code>/<int:player>')
def show_question(game_code, player):
    #global games, active_games
    if GAME_DB:
        games, active_games = read_from_db(True)
        locked = True
    game = games[game_code]
    #p('in show_question', game_code, game.is_on(), game.last_answer_number(player), game.total_questions(), game.available_questions)
    # the first player asking for a new question after already answering the last question of the quiz -
    # triggers ending the game
    '''
    if RANDOM and game.is_on() and len(game.available_questions) == 0: # no more questions left
        end_game = True
    elif not RANDOM and
    '''
    if game.is_on() and game.last_answer_number(player) == game.total_questions(): # no more questions left
        end_game = True
    else:
        end_game = False
    if end_game:
        game.end()
        active_games -= 1
        if GAME_DB:
            update_db(games, active_games)
            locked = False
    #p('in show_question', game_code, active_games, game.is_on(), games)
    if not game.is_on():
        pusher_client.trigger(f'my-channel-{game_code}', 'my-event', {'tag': 'end', 'msg': f"game {game_code} finished"})
        return show_summary(game_code, player)
    # while game is on, the first player requesting a new question triggers advancing the game to the next question
    if game.last_answer_number(player) == game.current_question():
        game.new_question(player)  # we pass palyer just to log who asked first for new question
        if GAME_DB:
            update_db(games, active_games)
            locked = False
    if GAME_DB:
        if locked:
            db.session.close()
            #db.engine.connect()
    question_info = f"question {game.current_question()} out of {game.total_questions()}"
    #p('in show_question1:', game_code, active_games, game.is_on(), question_info, game.video_source(), games)
    return render_template(f'game/question{session["mobile"]}.html', game_code=game_code, player=player, video_source=game.video_source(),
                           question_info=question_info, question_delay=question_delay)

#@app.route('/get_answer/<int:game_code>/<int:player>/<int:answer>')
def get_answer(game_code, player, answer):
    #global games
    if GAME_DB:  games, active_games = read_from_db(True)
    game = games[game_code]
    game.save_answer(player, answer)
    if GAME_DB: update_db(games, active_games)
    return wait_for_answers(game_code, player)

#@app.route('/wait_for_answers/<int:game_code>/<int:player>')
def wait_for_answers(game_code, player, showed_answer=False):
    #global games#, answer_delay, question_delay
    if GAME_DB: games, active_games = read_from_db()
    game = games[game_code]
    last_answer = game.last_answer(player)

    p(f'in wait_for_answer, player={player}, showed_answer={showed_answer}, last_answer={last_answer}, question_is_due={game.question_is_due()}, curr_question={game.current_question()}, last_answer_number={game.last_answer_number(player)}')
    # if everyone already answered or player's time is up - show the answer screen
    # last_answer=0 means player did not answer until the time is due
    # if last_answer_number(player) < curr_question it means the next question is already started and no need to wait for others (they all answered or the time expired)
    if game.question_is_due() or last_answer == 0 or not showed_answer or game.current_question() > game.last_answer_number(player): # did not show correct/not correct screen
        if not showed_answer:
            player_success_info = 'You are correct!' if game.is_answer_correct(last_answer) else str()
            if game.number_of_players() == 1:
                all_players_success_info = str()
            else:
                correct_answers_from_others = game.correct_answers(game.current_question()) -\
                                              game.is_answer_correct(last_answer)
                all_players_success_info = f"correct answers from others: {correct_answers_from_others}"
            p(f'in wait_for_answer showing answer for: player={player}')
            return render_template(f'game/answer{session["mobile"]}.html', game_code=game_code,\
                               player=player,\
                               poster_source=game.poster_source(),\
                               answer_delay=answer_delay,\
                               player_success_info=player_success_info,\
                               all_players_success_info=all_players_success_info)
        pusher_client.trigger(f'my-channel-{game_code}', 'my-event', {'tag': 'next', 'msg': "show next question"})
        p(f'in wait_for_answer show_question for: player={player}')
        return show_question(game_code, player)
    time_remains = max( # keep on waiting for other players' answers
        0,
        int(question_delay - (time.time() - game.current_question_start_time()) + answer_delay)#.total_seconds())
    )
    #time_info = f"maximum seconds remaining: {time_remains}"
    players_info = f"answered so far: {game.players_answered_yet()} players"
    p(f'in wait_for_answer wait for others for: player={player}, time_remains={time_remains}')
    return render_template(f'game/wait_for_answers{session["mobile"]}.html', game_code=game_code, player=player,
                           time_info=time_remains, players_info=players_info)

#@app.route('/get_answer/<int:game_code>/<int:player>')
def show_summary(game_code, player):
    #global games
    if GAME_DB:  games, active_games = read_from_db(True)
    game = games[game_code]
    scores = game.scores()
    if not bool(scores):
        game.calc_scores(player)
        if GAME_DB: update_db(games, active_games)
        scores = game.scores()
    elif GAME_DB:
            db.session.close()
            #db.engine.connect()
    all_players_scores_info = game.winner_info() if game.number_of_players() > 1 else str()
    #x = game.winner_info() if game.number_of_players() > 1 else str()
    scores_dict = dict(scores)
    if player in scores_dict:
        player_score_info = f"You had {scores_dict[player]} correct answers out of {game.total_questions()}"
    else:
        player_score_info = str()
    return render_template(f'game/summary{session["mobile"]}.html', game_code=game_code, player=player, level=game.level(),
                           player_score_info=player_score_info, all_players_scores_info=all_players_scores_info)

@dataclass
class Game:
    game_level: int = 1
    players: int = 0
    answers: dict = field(default_factory=dict)
    #game_is_on = False
    game_is_on: bool = False
    game_start_time: time = time.time()
    curr_question: int = 0
    curr_question_start_time: time = game_start_time
    game_scores: list = field(default_factory=list)
    game_winner_info: str = str()
    available_questions: list = field(default_factory=list)

    def start(self):
        self.game_is_on = True
        self.game_start_time = time.time()
        if RANDOM:
            random.seed()
            self.available_questions = random.sample(range(1, 11), 10)
        #p('in start', self.available_questions, self.game_start_time)

    def end(self):
        #global active_games
        self.game_is_on = False

    def is_on(self):
        return self.game_is_on

    def start_time(self):
        return self.game_start_time

    def current_question(self):
        return self.curr_question

    def total_questions(self):
        return len(movies[self.game_level])

    def video_source(self):
        global movies
        q = self.current_question()
        if RANDOM:
            #p('in video_source', q, self.available_questions, self.available_questions[q - 1], movies[self.game_level])
            q = self.available_questions[q - 1]
        return(movies[self.game_level][q]['video_source'])

    def poster_source(self):
        global movies
        q = self.current_question()
        if RANDOM:
            #p('in video_source', q, self.available_questions, self.available_questions[q - 1], movies[self.game_level])
            q = self.available_questions[q - 1]  # the index of the list starts from 0 and not 1
        return(movies[self.game_level][q]['poster_source'])

    def add_player(self):
        self.players += 1
        return self.players

    def number_of_players(self):
        return self.players

    def new_question(self, player):
        '''
        if RANDOM:
            q = random.randint(1, self.total_questions())
            while q not in self.available_questions:
                q = random.randint(1, self.total_questions())
            p('new q0:', q, self.available_questions)
            self.available_questions.pop(self.available_questions.index(q))
            self.current_question() = q
            p('new q1:', q, self.available_questions)
        else:
        '''
        self.curr_question += 1
        self.curr_question_start_time = time.time()
        p(f'in new question, curr_question={self.curr_question}, player={player}')

    def current_question_start_time(self):
        return self.curr_question_start_time

    def save_answer(self, player, answer):
        if player not in self.answers:
            self.answers[player] = {}
        self.answers[player][self.current_question()] = {'answer': answer, 'is_correct': self.is_answer_correct(answer)}
        p(f'in save_answer, player={player}, current_question={self.current_question()}, {self.available_questions}, {self.available_questions[self.current_question() - 1]}, {self.answers[player]}')

    def is_answer_correct(self, answer):
        q = self.current_question()
        if RANDOM:
            q = self.available_questions[q - 1]
        return answer == movies[self.game_level][q]['correct_answer']

    def correct_answers(self, question):
        correct_answers = 0
        for player in range(1, self.number_of_players() + 1):
            if player in self.answers:
                if question in self.answers[player]:
                    if self.answers[player][question]['is_correct']:
                        correct_answers += 1
        return correct_answers

    def last_answer(self, player):
        if player not in self.answers:
            return -1
        last_answer_number = self.last_answer_number(player) # can not use curr_question because another player already advanced the counter
        p(f'in last answer, player={player}, last_answer_number={last_answer_number}, current_question={self.current_question()}, {self.answers[player]}')
        #return self.answers[player][self.current_question()]['answer']  # if player did not answer 1 or 2 then it means time is up and the answer=0
        return self.answers[player][last_answer_number]['answer']  # if player did not answer 1 or 2 then it means time is up and the answer=0

    def last_answer_number(self, player):
        if player not in self.answers:
            return 0
        '''
        if RANDOM:
            return list(self.answers[player].keys())[-1]
        '''
        return max(self.answers[player].keys())

    def players_answered_yet(self):
        players_answered = 0
        for player in range(1, self.number_of_players() + 1):
            if player in self.answers:
                if self.current_question() in self.answers[player]:
                    players_answered += 1
        return players_answered

    def question_is_due(self):
        # check if question time is due
        #global question_delay, comm_delay
        if time.time() - self.current_question_start_time() > question_delay + answer_delay: #comm_delay:
            return True
        # check if all players already answered
        players_answered = 0
        for player in range(1, self.number_of_players()+1):
            if player not in self.answers:
                break
            if self.current_question() not in self.answers[player]:
                break
            players_answered += 1
        return players_answered == self.number_of_players()

    def calc_scores(self, curr_player):
        scores = dict()
        for player in self.answers:
            scores[player] = sum(player_answer['is_correct'] for player_answer in self.answers[player].values())
        if len(scores) == 0:
            return

        self.game_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        winner, top_score = self.game_scores[0]
        winner_info = f"PLAYER {winner}" if winner != curr_player else "YOU ARE!"
        self.game_winner_info = f"Top score, with {top_score} correct answers: {winner_info}"
        for player, score in self.game_scores[1:]:
            if score != top_score:
                break
            self.game_winner_info = f"{self.game_winner_info}, PLAYER {player}"

    def scores(self):
        return self.game_scores

    def winner_info(self):
        return self.game_winner_info

    def level(self):
        return self.game_level
