# Hermes - TSG Communication Application

Web application for The SCRIPT Group to use for sending WhatsApp messages and E-Mails to a set of event registrants at once

This requires 5 configuration variables set in a JSON file (`data.json`) in the home directory :<br/>
`browser` - Browser you want selenium to use. Currently configured only for Google Chrome (chrome) and Mozilla Firefox (firefox)<br/>
`driver-path` - Path to your chromedriver/geckodriver executable<br/>
`login-api` - API URL to verify user login credentials<br/>
`table-api` - API URL to get the list of participants<br/>
`events-api` - API URL to get the list of events<br/>
`email-api` - API URL to send emails to registrants using Sendgrid API from hades<br/>
`log_channel` - Telegram channel ID where activity logs are sent<br/>
`telebot_api_key` - API Key of bot used to send activity logs to Telegram<br/>

A basic setup script is included in the repo, that allows the application to function perfectly on Ubuntu 18.04+

## To send messages
- Login with your `tsg id`
- Select event from list of events
- Enter ids to send message to, seperated by a space / enter `all` to send to all registrants
- Enter subject _if sending mail_
- Enter message
    - For E-Mails, the message is to be written as HTML content
    - For WhatsApp, write as you would in mobile app. Write `\n` whenever you want to send a new message.
- Select WhatsApp and/or E-Mail options
- Click on send
- Scan QR code from WhatsApp mobile _if sending WhatsApp messages_