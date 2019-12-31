import requests
from emoji import emojize
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from time import sleep

whatsapp_api = 'https://api.whatsapp.com/send?phone=91'  # Format of url to open chat with someone

# dict with list of functions for each browser
driver = {
    'firefox': [webdriver.Firefox, webdriver.FirefoxOptions],
    'chrome': [webdriver.Chrome, webdriver.ChromeOptions]
}


# to make browser wait till a certain element is loaded onto the screen
def waitTillElementLoaded(browser, element, time=60, identifier=By.XPATH):
    element_present = ec.presence_of_element_located((identifier, element))
    WebDriverWait(browser, time).until(element_present)


def getData(url, table, headers, ids):
    names_list = []  # List of all names
    numbers_list = []  # List of all numbers

    # Get data from our API
    api_data = requests.get(url=url, params={'table': table}, headers=headers).json()
    if ids != 'all':
        api_data = [user for user in api_data if user['id'] in ids]

    # Add names and numbers to respective lists
    for user in api_data:
        names_list.append(user['name'])
        numbers_list.append(user['phone'].split('|')[-1])

    return names_list, numbers_list


# Method to start a new session of WhatsApp Web for web app
def startWebSession(browser_type, driver_path):
    # set browser options
    options = driver[browser_type][1]()
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/77.0.3865.120 Safari/537.36")
    options.headless = True
    browser = driver[browser_type][0](executable_path=driver_path, options=options)  # create driver object

    browser.get('https://web.whatsapp.com/')  # opening whatsapp in browser
    print('whatsapp opened')

    # Get the qr image
    waitTillElementLoaded(browser,
                          '/html/body/div[1]/div/div/div[2]/div[1]/div/div[2]/div/img')  # wait till qr is loaded
    # retreive qr image
    qr = (browser.find_element_by_xpath('/html/body/div[1]/div/div/div[2]/div[1]/div/div[2]/div/img')
          .get_attribute('src'))
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

    waitTillElementLoaded(browser, "use WhatsApp Web", identifier=By.LINK_TEXT)  # wait till the link is loaded
    browser.find_element_by_link_text("use WhatsApp Web").click()  # click on link to open chat
    print('opened chat')

    # Wait till the text box is loaded onto the screen, then type out and send the full message
    xpath = "/html/body/div[1]/div/div/div[4]/div/footer/div[1]/div[2]/div/div[2]"  # xpath to text box
    waitTillElementLoaded(browser, xpath, time=time)

    browser.find_element_by_xpath(xpath).send_keys(
        emojize(f"Hey, {name} :wave:\n", use_aliases=True))  # welcome note

    browser.find_element_by_xpath(xpath).send_keys(msg[0])  # send part before any newlines

    # for all subsequent parts, first press shift+enter to add a new line, then type out that part
    for m in msg[1:]:
        browser.find_element_by_xpath(xpath).send_keys(Keys.SHIFT + Keys.ENTER, Keys.SHIFT, m)

    browser.find_element_by_xpath(xpath).send_keys(
        emojize("\n- SCRIPT bot :robot_face:\n", use_aliases=True))  # end note

    print('sent')

    sleep(3)  # Just so that we can supervise, otherwise it's too fast

    return name + ' : ' + api
