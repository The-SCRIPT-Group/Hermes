# Hermes - TSG Communication Application

Web application for The SCRIPT Group to use for sending WhatsApp messages to a set of event registrants at once

This requires 5 configuration variables set either in your environment, or in a JSON file :<br/>
`browser` - Browser you want selenium to use. Currently configured only for Google Chrome (chrome) and Mozilla Firefox (firefox)<br/>
`driver-path` - Path to your chromedriver/geckodriver executable<br/>
`login-api` - API URL to verify user login credentials<br/>
`table-api` - API URL to get the list of participants<br/>
`events-api` - API URL to get the list of events<br/>
`log_channel` - Telegram channel ID where activity logs are sent<br/>
`telebot_api_key` - API Key of bot used to send activity logs to Telegram<br/>

A basic setup script is included in the repo, that allows the application to function perfectly on Ubuntu 18.04+
