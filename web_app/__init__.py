import json
import os
import traceback
from base64 import b64encode as bs
from threading import Thread

from flask import Flask, render_template, session, request, url_for, redirect
from requests import get, post
from selenium.common.exceptions import TimeoutException

from web_app import whatsapp as meow
from web_app.telegram import TG

app = Flask(__name__)
app.secret_key = 'messenger_of_the_gods'
browser = {}

# Get config data from json / env
if os.path.exists(os.path.join(os.getcwd().replace('web_app', ''), 'data.json')):
    with open(os.path.join(os.getcwd().replace('web_app', ''), 'data.json'), 'r') as f:
        data = json.load(f)
else:
    print("You don't have configuration JSON, go away")
    exit(1)

tg = TG(data['telebot_api_key'])  # object used to log data to telegram


# log messages to tg channel
def log(message, doc=None):
    if doc is not None:
        tg.send_document(data['log_channel'], f"<b>Hermes</b> :\n{message}", doc)
    else:
        tg.send_message(data['log_channel'], f"<b>Hermes</b> :\n{message}")


# wrapper; only execute function if user is logged in
def login_required(func):
    def inner(*args, **kwargs):
        if 'username' in session:  # since on login the username is set as a session variable
            return func(*args, **kwargs)
        else:
            return render_template('begone.html')

    return inner


# homepage - shows login details
@app.route('/')
def home():
    return render_template('index.html')


# login user
@app.route('/login', methods=['POST'])
def login():
    headers = {'Credentials': bs(str(request.form['username'] + '|' + request.form['password']).encode())}

    if post(url=data['login-api'], headers=headers, allow_redirects=False).status_code == 200:
        # set session variables
        session['username'] = request.form['username']
        session['headers'] = headers

        # log info onto terminal and telegram channel
        print('Logged in ', session['username'])
        log(f"<code>{session['username']}</code> logged in")
        return redirect(url_for('form'))

    else:
        return render_template('begone.html')


# display message details form
@login_required
@app.route('/form')
def form():
    return render_template(
        'form.html',
        events=get(url=data['events-api'], headers=session['headers']).json()
    )


# display loading page while sending messages
@login_required
@app.route('/submit', methods=['POST'])
def submit_form():
    if 'whatsapp' not in request.form and 'sendgrid' not in request.form:  # neither option was selected
        return render_template('begone.html')

    if 'sendgrid' in request.form:  # emails are to be sent
        # set kwargs in a seperate dict, since threaded function cannot access session or request objects
        params = dict(request.form)
        params['headers'] = session['headers']
        params['username'] = session['username']
        Thread(target=send_mail, kwargs=params).start()  # start procedure in a parallel thread

    if 'whatsapp' in request.form:  # whatsapp messages are to be sent
        # set info as session variables since they need to be accessed later, and are different for each session
        session['msg'] = list(map(lambda x: x.replace("\\n", "\n"),
                                  request.form['content'].split('\n')))  # split the message by new lines
        session['table'] = request.form['table']
        session['ids'] = request.form['ids']
        return render_template('loading.html', target='/qr')  # show loading page while selenium opens whatsapp web

    # if whatsapp messages are not to be sent, go back to form with a success message
    return render_template(
        'form.html', msg="Sending Messages!",
        events=get(url=data['events-api'], headers=session['headers']).json()
    )


# send emails
def send_mail(**kwargs):
    post(url=data['email-api'], data=kwargs, headers=kwargs['headers'])  # post call to hades

    # Get data from our API
    if kwargs['ids'] == 'all':
        names = meow.getData(data['table-api'], kwargs['table'], kwargs['headers'], 'all')[0]
    else:
        names = meow.getData(
            data['table-api'],
            kwargs['table'], kwargs['headers'],
            list(map(lambda x: int(x), kwargs['ids'].split(' ')))
        )[0]

    # write names of recipients to a file
    newline = '\n'
    with open('sendgrid_list.txt', 'w') as file:
        file.write(f"E-Mails sent to :\n{newline.join(names)}")

    # log file to telegram channel
    tg.send_chat_action(data['log_channel'], 'upload document')
    log(f"List of people who received E-Mails during run by user <code>{kwargs['username']}</code>",
        "sendgrid_list.txt")
    os.remove('sendgrid_list.txt')  # no need for file anymore

    print(kwargs['username'], "Done sending e-mails")


# display qr code to scan
@login_required
@app.route('/qr')
def qr():
    print('started driver session for ' + session['username'])
    browser[session['username']], qr_img = meow.startWebSession(data['browser'], data['driver-path'])
    return render_template('qr.html', qr=qr_img)


# start sending messages on whatsapp
@login_required
@app.route('/send', methods=['POST', 'GET'])
def send():
    # wait till the chat search box is loaded, so you know you're logged in
    meow.waitTillElementLoaded(browser[session['username']],
                               '/html/body/div[1]/div/div/div[3]/div/div[1]/div/label/input')
    print(session['username'], "logged into whatsapp")

    # send messages
    Thread(target=send_messages, kwargs=dict(session)).start()

    return render_template(
        'form.html', msg="Sending Messages!",
        events=get(url=data['events-api'], headers=session['headers']).json()
    )


# send messages on whatsapp
def send_messages(**kwargs):
    # list to store successes and failures
    messages_sent_to = []
    messages_not_sent_to = []

    try:
        # Get data from our API
        if kwargs['ids'] == 'all':
            names, numbers = meow.getData(data['table-api'], kwargs['table'], kwargs['headers'], 'all')
        else:
            names, numbers = meow.getData(data['table-api'], kwargs['table'], kwargs['headers'],
                                          list(map(lambda x: int(x), kwargs['ids'].strip().split(' '))))

        # Send messages to all registrants
        for num, name in zip(numbers, names):
            try:
                messages_sent_to.append(
                    meow.sendMessage(num, name, kwargs['msg'], browser[kwargs['username']], time=30)
                )
            except TimeoutException:
                print("chat could not be loaded for", name)
                messages_not_sent_to.append(name)

        # Close browser
        browser[kwargs['username']].close()
        print('closed driver for ' + kwargs['username'])

    except Exception as e:
        print(e)
        traceback.print_exc()

    finally:
        # write all successes and failures to a file
        newline = '\n'
        with open('whatsapp_list.txt', 'w') as file:
            file.write(
                f"Messages sent to :\n{newline.join(messages_sent_to)}\n\n"
                f"Messages not sent to :\n{newline.join(messages_not_sent_to)}")

        # log file to telegram channel
        tg.send_chat_action(data['log_channel'], 'upload document')
        log(f"List of people who received and didn't receive WhatsApp messages during run by user "
            f"<code>{kwargs['username']}</code>",
            "whatsapp_list.txt")
        os.remove('whatsapp_list.txt')  # no need for file anymore

        print(kwargs['username'], "done sending messages!")
