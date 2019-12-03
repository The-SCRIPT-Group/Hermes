import json
import os
from base64 import b64encode as bs
from random import choice
from string import ascii_letters, digits
import traceback

from emoji import demojize
from flask import Flask, render_template, session, request, redirect, url_for
from requests import get, post
from selenium.common.exceptions import TimeoutException

from web_app import whatsapp as meow

app = Flask(__name__)
app.secret_key = 'messenger_of_the_gods'
browser = {}

# Get config data from json / env
if os.path.exists(os.path.join(os.getcwd().replace('web_app', ''), 'data.json')):
    with open(os.path.join(os.getcwd().replace('web_app', ''), 'data.json'), 'r') as f:
        data = json.load(f)
else:
    try:
        data = {
            'api-token': os.environ['API_TOKEN'],
            'browser': os.environ['BROWSER'],
            'driver-path': os.environ['DRIVER_PATH'],
            'table-api': os.environ['TABLE_API_URL'],
            'events-api': os.environ['EVENTS_API_URL'],
        }
    except KeyError:
        print("You don't have configuration JSON or os.environment variables set, go away")
        exit(1)


# wrapper; only execute function if user is logged in or request from qrstuff
def authorized(func):
    def inner(*args, **kwargs):
        if 'username' in session:
            return func(*args, **kwargs)
        else:
            return render_template('begone.html')

    return inner


def dogbin(content):
    # Save names of who all are gonna get messages in dogbin
    response = json.loads(post("https://del.dog/documents", content).content.decode())
    print(response)
    return 'https://del.dog/{}'.format(response['key'])


# homepage - basically come here after he's logged in qrstuff
@app.route('/')
def home():
    print(session)
    return render_template('index.html')


# login user and retrieve qr
@app.route('/login', methods=['POST'])
def login():
    creds = str(request.form['username'] + '|' + request.form['password'])
    if post(url=data['login-api'], headers={'Credentials': bs(creds.encode())},
            allow_redirects=False).status_code == 200:
        session['username'] = request.form['username']
        session['credentials'] = bs(creds.encode())
        session['id'] = ''.join([choice(ascii_letters + digits) for _ in range(32)])
        return redirect(url_for('qr'))
    else:
        return render_template('begone.html')


# display qr code to scan
@authorized
@app.route('/qr')
def qr():
    print('started driver session for ' + session['username'])
    browser[session['id']], qr_img = meow.startWebSession(data['browser'], data['driver-path'])
    return render_template('qr.html', qr=qr_img)


# display message details form
@authorized
@app.route('/form')
def form():
    return render_template('form.html', events=json.loads(
        get(
            url='https://thescriptgroup.herokuapp.com/api/events', headers={'Credentials': session['credentials']}
        ).text))


# send messages on whatsapp
@authorized
@app.route('/send', methods=['POST'])
def send():
    """
    set the message in the format -
    Hey name :wave:
    <msg taken from form>
    - SCRIPT bot :robot_face:
    """
    msg = (
            'Hey, {} :wave:\n' +
            demojize(request.form['message']) + '\n' +
            '- SCRIPT bot :robot_face:\n'
    )

    messages_sent_to = []
    messages_not_sent_to = []

    try:
        # Wait till the text box is loaded onto the screen
        meow.waitTillElementLoaded(browser[session['id']], '/html/body/div[1]/div/div/div[4]/div/div/div[1]')

        # Get data from our API
        if request.form['ids'] == 'all':
            names, numbers = meow.getData(data['table-api'], request.form['table'], session['credentials'], 'all')
        else:
            names, numbers = meow.getData(data['table-api'], request.form['table'], session['credentials'],
                                          list(map(lambda x: int(x), request.form['ids'].split(' '))))

        # Send messages to all entries in file
        for num, name in zip(numbers, names):
            try:
                messages_sent_to.append(meow.sendMessage(num, name, msg, browser[session['id']], time=30))
            except TimeoutException:
                print("chat could not be loaded for", name)
                messages_not_sent_to.append(name)

        # Close browser
        browser[session['id']].close()
        print('closed driver session for ' + session['username'])

    except Exception as e:
        print(e)
        traceback.print_exc()

    finally:
        # first \n just to make sure the paste content is never empty
        sent_list = dogbin('Messages sent to :\n' + '\n'.join(messages_sent_to))
        not_sent_list = dogbin('Messages not sent to :\n' + '\n'.join(messages_not_sent_to))
        # Send the url to dogbin on the chat
        return render_template('success.html', sent_list=sent_list, not_sent_list=not_sent_list)


# for testing purpose
@app.route('/begone')
def begone():
    return render_template('begone.html')


# for testing purpose
@app.route('/success')
def success():
    return render_template('success.html', sent_list='/', not_sent_list='/')
