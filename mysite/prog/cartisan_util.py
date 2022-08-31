# -*- coding: utf-8 -*-
"""
Created on Mon Aug 29 23:57:38 2022

@author: drbarak
"""
SQLALCHEMY_DATABASE_URI = "mysql+mysqlconnector://{username}:{password}@{hostname}/{databasename}".format(
    username="root",
    password="password",
    hostname="localhost:3306",
    databasename="sample_staff",
)

import numpy as np
import sys
from flask_app import db, logDB

def val(x):
  if (isinstance(x, (int, np.integer)) or isinstance(x, (float, np.float))) and not isinstance(x, (bool, np.bool)):
    return x
  try:
    return int(x) if not x is None else 0
  except ValueError:
    try:
      return float(x)
    except ValueError:
      return 0

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
    try:  # if here before session is defined
        if globals.write_to_log:
            row = logDB(line=msg)
            try:
                db.session.add(row)
                db.session.commit()
                if row.id is None:
                    msg = 'error adding user_login'
                    print(msg, file=sys.stderr, flush=True)
            except:
                pass
    except:
        pass

import smtplib
from email.message import EmailMessage

def send_email(text='Message from WeatherBot', subject='New Session', to="drbarak@talkie.co.il", ip='', src='Weatherbot'):
  msg = EmailMessage()
  msg.set_content(text)

  msg.set_content('')
  # Add the html version.  This converts the message into a multipart/alternative
  # container, with the original text message as the first part and the new html
  # message as the second part. (Note that the first part of the messge did not work for me and didnot displaed on the incomin email)
  msg.add_alternative('''
  <html>
    <head>
      <h1 style="text-align: center; color: red;">
        {subject}
      </h1>
    </head>

    <body>
      {text}
    </body>

  </html>
  '''.format(subject=subject, text=text), subtype='html')

  msg['Subject'] = f'{subject} from_ip={ip}'
  msg['From'] = f"{src} <dr.zvibarak@gmail.com>"
  msg['To'] = to

  try:
    smtpObj = smtplib.SMTP('smtp.gmail.com', 587)
    smtpObj.starttls()
#    smtpObj.login('dr.zvibarak@gmail.com', 'shushu1952')
    smtpObj.login('dr.zvibarak@gmail.com', 'dodwlzplnuarvqij')  # app specific password, as per Google enhanced security with 2-stage verification
            # the password was generated on 29/08/22022 at 00:30 for app named 'cartisan' in google
    smtpObj.send_message(msg)
    smtpObj.quit()
    print("Successfully sent email")
    return True
  except Exception as e:# SMTPException:
    print("Error: unable to send email")
    p(e)
    return False
