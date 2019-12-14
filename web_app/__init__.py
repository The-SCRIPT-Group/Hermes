import json
import os
import traceback
from base64 import b64encode as bs
from threading import Thread

from emoji import demojize
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

tg = TG(data['telebot_api_key'])


# log messages to tg channel
def log(message, doc=None):
    if doc is not None:
        tg.send_document(data['log_channel'], f"<b>Hermes</b> :\n{message}", doc)
    else:
        tg.send_message(data['log_channel'], f"<b>Hermes</b> :\n{message}")


# wrapper; only execute function if user is logged in or request from qrstuff
def authorized(func):
    def inner(*args, **kwargs):
        if 'username' in session:
            return func(*args, **kwargs)
        else:
            return render_template('begone.html')

    return inner


# homepage - basically come here after he's logged in qrstuff
@app.route('/')
def home():
    return render_template('index.html')


# login user and retrieve qr
@app.route('/login', methods=['POST'])
def login():
    creds = str(request.form['username'] + '|' + request.form['password'])
    if post(url=data['login-api'], headers={'Credentials': bs(creds.encode())},
            allow_redirects=False).status_code == 200:
        session['username'] = request.form['username']
        session['credentials'] = {'Credentials': bs(creds.encode())}
        print('Logged in ', session['username'])
        log(f"<code>{session['username']}</code> logged in")
        return redirect(url_for('form'))
    else:
        return render_template('begone.html')


# display message details form
@authorized
@app.route('/form')
def form():
    return render_template('form.html', events=json.loads(
        get(
            url=data['events-api'], headers=session['credentials']
        ).text))


# display loading page while sending messages
@authorized
@app.route('/submit', methods=['POST'])
def submit_form():
    if 'whatsapp' not in request.form and 'sendgrid' not in request.form:
        return render_template('begone.html')

    if 'sendgrid' in request.form:
        params = dict(request.form)
        params['credentials'] = session['credentials']
        params['username'] = session['username']
        Thread(target=send_mail, kwargs=params).start()

    if 'whatsapp' in request.form:
        # set message in correct format to send
        session['msg'] = (
                "Hey, {} :wave:\n" +
                demojize(request.form['content']) + "\n" +
                "- SCRIPT bot :robot_face:\n"
        )
        session['table'] = request.form['table']
        session['ids'] = request.form['ids']
        return render_template('loading.html', target='/qr')

    return render_template(
        'form.html', msg="Sending Messages!",
        events=json.loads(get(url=data['events-api'], headers=session['credentials']).text)
    )


# send emails
def send_mail(**kwargs):
    res = post(url=data['email-api'], data=kwargs, headers=kwargs['credentials'])
    print(res, res.text)

    # Get data from our API
    if kwargs['ids'] == 'all':
        names = meow.getData(data['table-api'], kwargs['table'], kwargs['credentials'], 'all')[0]
    else:
        names = meow.getData(
            data['table-api'],
            kwargs['table'], kwargs['credentials'],
            list(map(lambda x: int(x), kwargs['ids'].split(' ')))
        )[0]

    newline = '\n'
    with open('sendgrid_list.txt', 'w') as file:
        file.write(f"E-Mails sent to :\n{newline.join(names)}")

    tg.send_chat_action(data['log_channel'], 'upload document')
    log(f"List of people who received E-Mails during run by user <code>{kwargs['username']}</code>",
        "sendgrid_list.txt")
    os.remove('sendgrid_list.txt')

    print(kwargs['username'], "Done sending e-mails")


# display qr code to scan
@authorized
@app.route('/qr')
def qr():
    print('started driver session for ' + session['username'])
    browser[session['username']], qr_img = meow.startWebSession(data['browser'], data['driver-path'])
    return render_template('qr.html', qr=qr_img)


# send messages on whatsapp
@authorized
@app.route('/send', methods=['POST', 'GET'])
def send():
    # wait till the chat search box is loaded, so you know you're logged in
    meow.waitTillElementLoaded(browser[session['username']],
                               '/html/body/div[1]/div/div/div[3]/div/div[1]/div/label/input')
    print(session['username'], "logged into whatsapp")

    # send messages
    Thread(target=run_whatsapp, kwargs=dict(session)).start()

    return render_template(
        'form.html', msg="Sending Messages!",
        events=json.loads(get(url=data['events-api'], headers=session['credentials']).text)
    )


def run_whatsapp(**kwargs):
    messages_sent_to = []
    messages_not_sent_to = []

    try:
        # Get data from our API
        if kwargs['ids'] == 'all':
            names, numbers = meow.getData(data['table-api'], kwargs['table'], kwargs['credentials'], 'all')
        else:
            names, numbers = meow.getData(data['table-api'], kwargs['table'], kwargs['credentials'],
                                          list(map(lambda x: int(x), kwargs['ids'].split(' '))))

        # Send messages to all entries in file
        for num, name in zip(numbers, names):
            try:
                messages_sent_to.append(
                    meow.sendMessage(num, name, kwargs['msg'], browser[kwargs['username']], time=30))
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
        newline = '\n'
        with open('whatsapp_list.txt', 'w') as file:
            file.write(
                f"Messages sent to :\n{newline.join(messages_sent_to)}\n\n"
                f"Messages not sent to :\n{newline.join(messages_not_sent_to)}")

        tg.send_chat_action(data['log_channel'], 'upload document')
        log(f"List of people who received and didn't receive WhatsApp messages during run by user "
            f"<code>{kwargs['username']}</code>",
            "whatsapp_list.txt")
        os.remove('whatsapp_list.txt')

        print(kwargs['username'], "done sending messages!")
