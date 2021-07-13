# echo > /var/log/drbarak.pythonanywhere.com.error.log

from spacy.matcher import PhraseMatcher

from dateutil.parser import parse
from datetime import datetime
from wordtodigits import convert

from prog.chatbot_init import nlp, space_punct_dict
from prog.chatbot_init import p
from prog.chatbot_init import dayInWeek, dateToNum, listNlp, tz, NO_DAYS, datesDf

TODAY = 0

def is_valid_date(dt, disp=False, round=0):
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
      if round == 0 and len(dt) == 8 and 'month must be in 1..12' in str(e):
        dt = dt[4:] + dt[2:4] + dt[0:2]
        return is_valid_date(dt, round=1)
      if 'String does not contain a date' not in str(e):
        p(e)
      if disp: p('invalid:', dt)
      return False, None, None, None, None
  return False, None, None, None, None

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
    if disp: print(entity.text, entity.pos_, entity.head, entity.lemma_, entity.head.lemma_)
    if entity.pos_=='NUM':
      if disp: print("found number "+entity.text, entity.text.isdigit())
      if entity.text.isdigit():
          num = int(entity.text)
      else:
          #num = textToNumbers.get(entity.text, NO_DAYS)
          num_str = convert(entity.text)
          num = int(num_str) if num_str.isdigit() else NO_DAYS
      if disp: print ('number is', num)
      if entity.head.lemma_ == 'week': # if there is week add it to number to week and if not match it num of days
        if num != NO_DAYS:
          week = num
      elif entity.head.lemma_ == 'day': # new 05.07.2021
        days = num
  #if week > 0 and days == NO_DAYS:  days = 0
  if disp: p('get_number_period result = ', days, week)
  return days, week

def check_date(dateText, disp=False, israel=False):
  days, week, found_days, cur_days = NO_DAYS, 0, NO_DAYS, NO_DAYS
  rangeDays, days2, week2 = 1, NO_DAYS, NO_DAYS
  todayDayWeek = 0 # get day in week today
  dayInText = -NO_DAYS # get day in week by text
  f_string = " days={0}, week={1}, days2={4}, week2={5}, found_days={2}, cur_days={3}"
  range_days, weekend = 1, False # single day
  first_day = True  # did not find a day of the week (to know when do we 2 days for a range)
  if len(dateText) == 0:
    return NO_DAYS, 0
  # spacy did seperate 'tuesday next week' into 2 parts 'tuesday' 'next week' and
  # our function uses the 'next week' and ignores the 'tuesday' so we force
  # a comma before and after
  dateText_str = ', '.join([s for s in dateText])
  future_day = False #  if found a future day (in 2 dyas, on tuesday, ect))
  for text in dateText: # check if we get several date variables
    if len(text) == 0: continue
    if disp: p('text =', text, future_day)
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
          future_day = True
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
          future_day = True
        elif column == "thisweek" and len(dateText) == 1:  # 'thsi week' alone -> next 7 days
          return 0, 7
        if numFinal != NO_DAYS or days == NO_DAYS:
          days = numFinal
        #''' need this code for 'following day"
        if len(dateText) == 1 and not weekend:# and len(text) == 1: #even if the text consists of 2 words 'following day' since we found a match we can use the column index
          if disp: p(f"numFinal2 = {numFinal}")
          numFinal = dateToNum.get(column, NO_DAYS)
          if numFinal != NO_DAYS or days == NO_DAYS:
            return numFinal, range_days

        if disp: p(days, todayDayWeek, dayInText, future_day)
        # todayDayWeek is in the range 1=sunday to 7=saturday
        # dayInText is in the same range
        # in order to compare we need to convert both such the sunday = 8 (mon=1, tue=2...sat=7, sun=8)
        todayDayWeek_new = todayDayWeek if todayDayWeek > 1 else 8
        dayInText_new = dayInText if dayInText > 1 else 8
        if disp: p(days, todayDayWeek, dayInText, dayInText_new)
        if days != NO_DAYS:  # verify days match numOfdays (in case on Friday asked for "friday in 2 days" which is wrong)
          if column == "today" and days == 0:
            future_day = True
          elif column == "tomorrow" and days == 1:
            future_day = True
          elif column == "twoDays" and days == 2:
            future_day = True
          elif column == 'thisweek' and (dayInText_new >= todayDayWeek_new):  # this week must be day after today up to sunday
            future_day = True
          elif column == 'nextWeek' and week == 1:  # next week cannot have a contradiction because can be any day
            future_day = True
          else:
            days = NO_DAYS
        cur_days = days  # days for this text independent of prev columns
        break # found a match no need to check other column for this text
    if disp: print("1." + f_string.format(days, week, found_days, cur_days, days2, week2))
    if found_days == NO_DAYS: found_days = days
    if week == 0 and days == NO_DAYS and cur_days == NO_DAYS: # didn't find word in the DF dates
      days, week, todayDayWeek, dayInText, weekend, range_days = get_delta_days_weekday(text, dayInText, weekend, range_days, disp) # check day in week and return num of days and week
      if disp: print("2." + f_string.format(days, week, found_days, cur_days, days2, week2))
      if days != NO_DAYS and days != found_days and found_days != NO_DAYS:
        days = NO_DAYS
      elif found_days == NO_DAYS:
        found_days = days
      if (week == 0 or days == NO_DAYS) and 'next' not in text: # only if not range
        sav_days = days
        days, week = get_number_period(doc, disp) # check number of days/weeks
        if days == NO_DAYS and sav_days != NO_DAYS:
          days = sav_days
        #else: future_day = True
        if disp: print("3." + f_string.format(days, week, found_days, cur_days, days2, week2))
        # in english the week ends on Sunday, so if we r on:
        # sunday then next_week=0 weeks from now
        # monday then next_week=1 weeks from now
        # -> we calc days up to sunday, and add 1 week
      elif 'next' in text and 'week' not in text:
        week = 0
    if days2 == NO_DAYS:
      if ('next' in text or  # 'two days' without 'next' means 'in two days' which is not a range
            future_day):  # if already have the future day the next item is for range ('friday', '2 days'  means on 'friday for 2 days')
        days2, week2 = get_number_period(doc, disp) # check number of days/weeks because "3 days", can be for two options, num of dasy and range
        if week2 <= 0: week2 = NO_DAYS # to be consistent with week2 default
      if disp: print("3A. " + f_string.format(days, week, found_days, cur_days, days2, week2))
      if week == 0 and days == NO_DAYS and days2 == NO_DAYS and week2 == NO_DAYS: # check if get format
        if disp: p("check date format", text)
        is_date, year, month, day, ndays = is_valid_date(text, disp)
        if disp:  p(f"4. get date by format {year}-{month}-{day} num of days = {ndays}")
        if is_date:
          days = ndays
          week = 0
          future_day = True
        # if 2 named days (tuesday, sunday) means from tuesday to sunday)
      if days2 == NO_DAYS and days != NO_DAYS and text in dayInWeek and week2 == NO_DAYS:
        if first_day:
          first_day = False
          future_day = True
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
  if disp: p(f"range = {days2}, number of days = {days}, weekend={weekend}, week2={week2}")
  if days2 != NO_DAYS and days == NO_DAYS:
    if disp: p("dates with just number of days/week")
    days = days2
    if week2 != NO_DAYS: week = week2
  if (days2 != NO_DAYS or week2 != NO_DAYS) and days != NO_DAYS:
    if disp:  p("get range", week2, days2, days, len(dateText), weekend, dateText, 'next' not in dateText_str, rangeDays, future_day)
    if week2 == NO_DAYS: week2 = 0
    if days2 == NO_DAYS: days2 = 0
    rangeDays = days2 + week2 * 7
  if (len(dateText) == 1 and not weekend and
         'next' not in dateText_str): # in case 'next 2 days'
    rangeDays = 1
  elif weekend:
    rangeDays = range_days
  elif days == days2 and rangeDays == days and not future_day:
    days = 0
  range_days = rangeDays

  if disp: p("5. " + f_string.format(days, week, found_days, cur_days, range_days, week2))
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
    if todayDayWeek > dayInText and week > 0 and not future_day:
      week -= 1
    if range_days == 2 and weekend:
      if disp: p('weekend', days, org_days)
      if org_days == NO_DAYS or dayInText >= 6:
        if dayInText == 7: # if sunday there is one day left in the weekend
          if israel: # sunday is not the weekend in israel, only saturday
            range_days = 0
            if days == 0: days = 6 # six more days till next saturday
          elif week == 1: # next week
            days -= 1 # nextweekent starts on Saturday
          else:
            range_days = 1
        elif dayInText < 6: # not sunday and not staurday
          days = 6 - dayInText # number of days to saturday
          if israel: range_days = 1
        elif israel: range_days = 1
      elif len(dateText) > 1:  # must have more than one word (was gettuing here with 'next weekedn' only)
        days = NO_DAYS  # can not say 'monday, next weekend
    if days != NO_DAYS:
      if range_days == 0: range_days = 1 # it is identical but just to be compatible with prev tests (to shaow rane must be > 1)
      return week * 7 + days, range_days
  return NO_DAYS, 0

