from urllib3 import PoolManager
from urllib3.exceptions import ProtocolError

manager = PoolManager()  # create PoolManager object


# class to log data to telegram channel using a telegram bot
class TG:

    # constructor - set API key of telegram bot to be used for logging to channel
    def __init__(self, api_key):
        self.api_key = api_key  # API key of telegram bot

    # function to call telegram API with some request
    def send(self, function, data):
        # function - which function do you want telegram API to call
        # data - dictionary containing arguments to the function the API will call

        try:
            # POST call to telegram API
            return manager.request(
                "POST",
                f"https://api.telegram.org/bot{self.api_key}/{function}",
                fields=data,
            )
        except ProtocolError as e:
            print(e, e.__class__)
            with open("extra-logs.txt", "a") as f:
                f.write(str(data) + "\n\n\n")

    # function to log text messages to telegram channel
    def send_message(self, chat_id, message, parse_mode="HTML"):
        # chat_id - ID of channel to which text message is to be logged
        # message - the content of the text message to be logged
        # parse_mode - what the text message is to be parsed as, defaults to HTML

        # create dictionary with all information passed as arguments to be passed to send function
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode,
        }

        return self.send("sendMessage", data)  # call telegram API to log text message

    # function to display a chat action to the telegram channel
    def send_chat_action(self, chat_id, action):
        # chat_id - id of the telegram channel
        # action - chat action to be displayed

        # create dictionary with all information passed as arguments to be passed to send function
        data = {
            "chat_id": chat_id,
            "action": action,
        }

        return self.send("sendChatAction", data)  # call telegram API to display chat action in channel

    # function to log a document to telegram channel
    def send_document(
            self,
            chat_id,
            caption,
            file_name,
            disable_notifications=False,
            parse_mode="HTML",
    ):
        # chat_id - ID of channel to which text message is to be logged
        # caption - the content of the text caption to be logged with the document
        # file_name - name of the file to be sent as a document

        # create dictionary with all information passed as arguments to be passed to send function
        data = {
            "caption": caption,
            "chat_id": chat_id,
            "document": (file_name, open(file_name, "rb").read()),
            "disable_notification": disable_notifications,
            "parse_mode": parse_mode,
        }

        return self.send("sendDocument", data)  # call telegram API to log document
