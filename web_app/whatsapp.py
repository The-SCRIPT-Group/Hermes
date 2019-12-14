import json

import requests
from emoji import emojize
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep

whatsapp_api = 'https://api.whatsapp.com/send?phone=91'  # Format of url to open chat with someone

driver = {
    'firefox': [webdriver.Firefox, webdriver.FirefoxOptions],
    'chrome': [webdriver.Chrome, webdriver.ChromeOptions]
}


def waitTillElementLoaded(browser, element, time=10000):
    element_present = ec.presence_of_element_located((By.XPATH, element))
    WebDriverWait(browser, time).until(element_present)


def waitTillLinkLoaded(browser, element):
    try:
        element_present = ec.presence_of_element_located((By.LINK_TEXT, element))
        WebDriverWait(browser, 10000).until(element_present)
    except TimeoutException:
        print('Timed out waiting for page to load')


def getData(url, table, credentials, ids):
    names_list = []  # List of all names
    numbers_list = []  # List of all numbers

    # Get data from our API
    api_data = json.loads(requests.get(url=url, params={'table': table}, headers=credentials).text)

    if ids == 'all':
        ids = list(map(lambda x: x['id'], api_data))

    # Add names and numbers to respective lists
    for user in api_data:
        if int(user['id']) in ids:
            names_list.append(user['name'])
            numbers_list.append(user['phone'].split('|')[-1])

    return names_list, numbers_list


# Method to start a new session of WhatsApp Web for web app
def startWebSession(browser_type, driver_path):
    # set browser options
    options = driver[browser_type][1]()
    options.add_argument(
        "user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 "
        "Safari/537.36")
    options.headless = True
    browser = driver[browser_type][0](executable_path=driver_path, options=options)  # create driver object

    browser.get('https://web.whatsapp.com/')  # opening whatsapp in browser
    print('whatsapp opened')

    # Get the qr image
    waitTillElementLoaded(browser,
                          '/html/body/div[1]/div/div/div[2]/div[1]/div/div[2]/div/img')  # wait till qr is loaded
    qr = browser.find_element_by_xpath(
        '/html/body/div[1]/div/div/div[2]/div[1]/div/div[2]/div/img').get_attribute('src')  # retreive qr image
    print('qr saved')

    return browser, qr  # returning the driver object and qr (b64 encoded)


# Method to send a message to someone
def sendMessage(num, name, msg, browser, time=10000):
    api = whatsapp_api + str(num)  # Specific url
    print(api, name)
    browser.get(api)  # Open url in browser
    print("opened whatsapp")

    waitTillElementLoaded(browser, '//*[@id="action-button"]')  # Wait till send message button is loaded
    browser.find_element_by_xpath('//*[@id="action-button"]').click()  # Click on "send message" button

    waitTillLinkLoaded(browser, "use WhatsApp Web")  # wait till the link is loaded
    browser.find_element_by_link_text("use WhatsApp Web").click()  # click on link to open chat
    print('opened chat')

    # Wait till the text box is loaded onto the screen, then type out and send the full message
    waitTillElementLoaded(browser, '/html/body/div[1]/div/div/div[4]/div/footer/div[1]/div[2]/div/div[2]', time=time)

    browser.find_element_by_xpath(
        '/html/body/div[1]/div/div/div[4]/div/footer/div[1]/div[2]/div/div[2]'
    ).send_keys(emojize(msg.format(name), use_aliases=True))
    print('sent')

    sleep(3)  # Just so that we can supervise, otherwise it's too fast

    return name + ' : ' + api
