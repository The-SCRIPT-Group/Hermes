from time import sleep

import requests
from emoji import emojize
from pandas import read_csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

# url to open chat with someone in whatsapp web
# append phone number of participant to the end of this string
whatsapp_api = 'https://api.whatsapp.com/send?phone=91'

# dict with list of functions for each browser
# first function for creating web driver
# second function for adding options to the created browser
driver = {
    'firefox': [webdriver.Firefox, webdriver.FirefoxOptions],
    'chrome': [webdriver.Chrome, webdriver.ChromeOptions],
}


# to make browser wait till a certain element is loaded onto the screen
def wait_till_element_loaded(browser, element, time=60, identifier=By.XPATH):
    element_present = ec.presence_of_element_located((identifier, element))
    WebDriverWait(browser, time).until(element_present)


# get all data of all participants from GET call to passed url
def get_data(url, table, headers, ids, path=""):
    # url - GET call to this url will return data of all participants from a certain event table
    # table - the event table from which participant data is to be returned
    # headers - contain the credentials of currently logged in user as a base64 encoded string
    #           in the format `username|password`, which is stored in header as the value to the key `Credentials`
    # ids - list of ids to be contacted
    # path - local path to the csv containing participants' details

    names_list = []  # List of all names
    numbers_list = []  # List of all numbers

    # Get data of participants from a certain event table
    if path != "":  # if source is a local csv
        api_data = read_csv(path).to_dict(orient='records')
    else:  # if source is hades
        api_data = requests.get(url=url, params={'table': table}, headers=headers).json()

    # select data of only those participants whose id is in the list of ids given as argument
    if ids != 'all':
        api_data = [user for user in api_data if user['id'] in ids]

    # Add names and numbers to respective lists
    for user in api_data:
        names_list.append(user['name'])
        numbers_list.append(str(user['phone']).split('|')[-1])

    return names_list, numbers_list


# Method to start a new session of WhatsApp Web for web app
def start_web_session(browser_type, driver_path):
    # set browser options
    options = driver[browser_type][1]()  # create Options object for respective browser
    options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/77.0.3865.120 Safari/537.36"
    )  # set user-agent to fool whatsapp web
    options.headless = True  # browser to be opened headless - server has no display

    # create driver object with above options
    browser = driver[browser_type][0](executable_path=driver_path, options=options)

    browser.get('https://web.whatsapp.com/')  # open whatsapp web in browser
    print('whatsapp opened')

    # wait till qr is loaded
    wait_till_element_loaded(browser, '/html/body/div[1]/div/div/div[2]/div[1]/div/div[2]/div/canvas')
    # retrieve qr code (base64 encoded image) from canvas
    qr = browser.execute_script(
        'return document.querySelector("html > body > div:nth-child(1) > div > div > div:nth-child(2) > div:nth-child(1) > div > div:nth-child(2) > div > canvas").toDataURL("image/png");'
    )
    print('qr saved')

    return browser, qr  # returning the driver object and qr


# Method to send a message to someone
def send_message(num, name, msg, browser, time=10000):
    # num - phone number to which message is to be sent
    # name - name(s) of participant(s)
    # msg - the message to be sent
    # browser - webdriver object using which whatsapp web is to be operated
    # time - number of seconds to wait for an element to load before raising Timeout exception

    api = whatsapp_api + str(num)  # Specific url to open chat with given number
    print(api, name)
    browser.get(api)  # Open url in browser
    print("opened whatsapp")

    # wait_till_element_loaded(browser, '//*[@id="action-button"]')  # Wait till send message button is loaded
    browser.find_element_by_xpath('//*[@id="action-button"]').click()  # Click on "send message" button

    wait_till_element_loaded(browser, "use WhatsApp Web", identifier=By.LINK_TEXT)  # wait till the link is loaded
    browser.find_element_by_link_text("use WhatsApp Web").click()  # click on link to open chat
    print('opened chat')

    # Wait till the text box is loaded onto the screen, then type out and send the full message

    xpath = "/html/body/div[1]/div/div/div[4]/div/footer/div[1]/div[2]/div/div[2]"  # xpath to text box
    wait_till_element_loaded(browser, xpath, time=time)  # wait till text box is loaded

    browser.find_element_by_xpath(xpath).send_keys(emojize(f"Hey {name} :wave:\n", use_aliases=True))  # welcome note

    browser.find_element_by_xpath(xpath).send_keys(msg[0])  # send part before any newlines

    # for all subsequent parts, first press shift+enter to add a new line, then type out that part
    for m in msg[1:]:
        browser.find_element_by_xpath(xpath).send_keys(Keys.SHIFT + Keys.ENTER, Keys.SHIFT, m)

    browser.find_element_by_xpath(xpath).send_keys(
        emojize("\n- SCRIPT bot :robot_face:\n", use_aliases=True)
    )  # end note

    print('sent')

    sleep(3)  # Just so that we can supervise, otherwise it's too fast

    # delete the chat
    browser.find_element_by_xpath(
        "/html/body/div[1]/div/div/div[4]/div/header/div[3]/div/div[3]"
    ).click()  # click on menu
    browser.find_element_by_xpath(
        "/html/body/div[1]/div/div/div[4]/div/header/div[3]/div/div[3]/span/div/ul/li[5]/div"
    ).click()  # click on delete option
    browser.find_element_by_xpath(
        "/html/body/div[1]/div/span[2]/div/div/div/div/div/div/div[2]/div[2]"
    ).click()  # click on confirmation button

    return name + ' : ' + api
