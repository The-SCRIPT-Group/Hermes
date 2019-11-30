# Hermes

Web application for The SCRIPT Group to use for sending WhatsApp messages to a bunch of people at once

This requires 5 configuration variables set either in your environment, or in a JSON file :<br/>
`api-token` - API token to access SCRIPT's API<br/>
`browser` - Browser you want selenium to use. Currently configured only for Google Chrome (chrome) and Mozilla Firefox (firefox)<br/>
`driver-path` - Path to your chromedriver/geckodriver executable<br/>
`table-api-url` - API URL to get the list of participants<br/>
`events-api-url` - API URL to get the list of events
