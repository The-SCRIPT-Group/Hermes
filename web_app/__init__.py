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

# create flask app and set a secret key for it to use to hash session variables
app = Flask(__name__)
app.secret_key = 'messenger_of_the_gods'

# dictionary to store all the webdriver objects created in each session

browser = {}

# Get config data from json
if os.path.exists(os.path.join(os.getcwd().replace('web_app', ''), 'data.json')):
    with open(os.path.join(os.getcwd().replace('web_app', ''), 'data.json'), 'r') as f:
        data = json.load(f)
else:
    print("You don't have configuration JSON, go away")
    exit(1)

tg = TG(data['telebot_api_key'])  # object used to log data to telegram


# log messages to tg channel
def log(message, doc=None):
    if doc is not None:  # if a document has been passed to log function, send it with send_document function
        tg.send_document(data['log_channel'], f"<b>Hermes</b> :\n{message}", doc)
    else:
        tg.send_message(data['log_channel'], f"<b>Hermes</b> :\n{message}")


# wrapper; only execute function if user is logged in
def login_required(func):
    def inner(*args, **kwargs):
        if 'username' in session:  # since on login the username is set as a session variable
            return func(*args, **kwargs)
        else:
            return render_template('begone.html')  # error page

    return inner


# homepage - shows login details
@app.route('/')
def home():
    return render_template('index.html')


# login user
@app.route('/login', methods=['POST'])
def login():
    # credentials for the API calls needs to be a base-64 encoded string in the format `username|password`
    # the credentials are sent in the header as value to the key `Credentials`
    headers = {'Credentials': bs(str(request.form['username'] + '|' + request.form['password']).encode())}

    # POST call to `login-api` essentially returns status code 200 only if credentials are valid
    if post(url=data['login-api'], headers=headers, allow_redirects=False).status_code == 200:
        # set session variables - username and the header that were verified in above POST call
        session['username'] = request.form['username']  # username
        session['headers'] = headers  # header stored for use in further API calls

        # log info onto terminal and telegram channel
        print('Logged in ', session['username'])
        log(f"<code>{session['username']}</code> logged in")

        return redirect(url_for('form'))  # redirect user to form upon login

    else:  # if credentials were determined as invalid by `login-api` POST call - status code returned not 200
        return render_template('begone.html')  # error page


# display message details form
@login_required
@app.route('/form')
def form():
    # events is the list of all the events that the currently logged in user can access
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
        # set kwargs in a separate dict, since threaded function cannot access session or request objects
        params = dict(request.form)
        params['headers'] = session['headers']  # base64 encoded credentials of currently logged in user
        params['username'] = session['username']  # username of currently logged in user
        Thread(target=send_mail, kwargs=params).start()  # start procedure in a parallel thread

    if 'whatsapp' in request.form:  # whatsapp messages are to be sent
        # set info as session variables since they need to be accessed later, and are different for each session
        session['msg'] = list(map(lambda x: x.replace("\\n", "\n"),
                                  request.form['content'].split('\n')))  # split the message by new lines
        session['table'] = request.form['table']  # the event table whose participants are to be contacted
        session['ids'] = request.form['ids']  # the ids (space separated) who are to be contacted
        return render_template('loading.html', target='/qr')  # show loading page while selenium opens whatsapp web

    # if whatsapp messages are not to be sent, go back to form with a success message
    # events is the list of all the events that the currently logged in user can access
    return render_template(
        'form.html', msg="Sending Messages!",
        events=get(url=data['events-api'], headers=session['headers']).json()
    )


# send emails
def send_mail(**kwargs):
    # POST call to `email-api` which makes Hades use sendgrid API to send emails to all participants whose id is listed
    # Subject and content of mail retrieved from HTML form and passed to this function as items in kwargs
    post(url=data['email-api'], data=kwargs, headers=kwargs['headers'])

    # Get data from our API
    # getData() returns two lists - first containing names and second containing numbers
    if kwargs['ids'] == 'all':  # retrieve names and numbers of all participants
        names = meow.getData(data['table-api'], kwargs['table'], kwargs['headers'], 'all')[0]
    else:  # retrieve names and numbers of participants whose id was listed by user
        # since ids are retrieved from form as a space separated string
        # split the string by space and convert all resultant list items to int
        names = meow.getData(
            data['table-api'],
            kwargs['table'], kwargs['headers'],
            list(map(lambda x: int(x), kwargs['ids'].split(' ')))
        )[0]

    # write names of recipients to a file
    newline = '\n'
    with open('sendgrid_list.txt', 'w') as file:
        file.write(f"E-Mails sent to :\n{newline.join(names)}")

    # log list of recipients to telegram channel
    tg.send_chat_action(data['log_channel'], 'upload document')
    log(f"List of people who received E-Mails during run by user <code>{kwargs['username']}</code>",
        "sendgrid_list.txt")
    os.remove('sendgrid_list.txt')  # no need for file once it is sent, delete from server

    print(kwargs['username'], "Done sending e-mails")


# display qr code to scan
@login_required
@app.route('/qr')
def qr():
    # create a webdriver object, open whatsapp web in the resultant browser and
    # display QR code on client side for user to scan

    print('started driver session for ' + session['username'])  # logging to server terminal

    # store the created webdriver object in browser dict
    # key - username of currently logged in user | value - webdriver object
    browser[session['username']], qr_img = meow.startWebSession(data['browser'], data['driver-path'])

    # the rendered HTML form, qr.html, automatically redirects to /send, which will load only once QR code is scanned,
    # the user is logged into whatsapp web and Hermes starts sending messages on whatsapp
    return render_template('qr.html', qr=qr_img)


# start sending messages on whatsapp
@login_required
@app.route('/send', methods=['POST', 'GET'])
def send():
    # wait till the chat search box is loaded, so you know you're logged into whatsapp web
    meow.waitTillElementLoaded(browser[session['username']],
                               '/html/body/div[1]/div/div/div[3]/div/div[1]/div/label/input')
    print(session['username'], "logged into whatsapp")

    # start thread that will send messages on whatsapp
    Thread(target=send_messages, kwargs=dict(session)).start()

    # go back to form with a success message
    # events is the list of all the events that the currently logged in user can access
    return render_template(
        'form.html', msg="Sending Messages!",
        events=get(url=data['events-api'], headers=session['headers']).json()
    )


# send messages on whatsapp
def send_messages(**kwargs):
    messages_sent_to = []  # list to store successes
    messages_not_sent_to = []  # list to store failures

    try:
        # Get data from our API
        # getData() returns two lists - first containing names and second containing numbers
        if kwargs['ids'] == 'all':
            names, numbers = meow.getData(data['table-api'], kwargs['table'], kwargs['headers'], 'all')
        else:
            names, numbers = meow.getData(data['table-api'], kwargs['table'], kwargs['headers'],
                                          list(map(lambda x: int(x), kwargs['ids'].strip().split(' '))))

        # Send messages to all registrants
        for num, name in zip(numbers, names):
            try:
                # send message to number, and then append name + whatsapp api link to list of successes
                messages_sent_to.append(
                    meow.sendMessage(num, name, kwargs['msg'], browser[kwargs['username']], time=30)
                )
            except TimeoutException:  # if chat with participant couldn't be loaded in 30 seconds
                print("chat could not be loaded for", name)
                messages_not_sent_to.append(name)  # append name to list of failures

        # Close browser
        browser[kwargs['username']].close()
        print('closed driver for ' + kwargs['username'])

    except Exception as e:  # for general exceptions
        print(e)
        traceback.print_exc()

    finally:
        # write all successes and failures to a file
        newline = '\n'
        with open('whatsapp_list.txt', 'w') as file:
            file.write(
                f"Messages sent to :\n{newline.join(messages_sent_to)}\n\n"
                f"Messages not sent to :\n{newline.join(messages_not_sent_to)}")

        # log file of all successes and failures to telegram channel
        tg.send_chat_action(data['log_channel'], 'upload document')
        log(f"List of people who received and didn't receive WhatsApp messages during run by user "
            f"<code>{kwargs['username']}</code>",
            "whatsapp_list.txt")
        os.remove('whatsapp_list.txt')  # no need for file once it is sent, delete from server

        print(kwargs['username'], "done sending messages!")
