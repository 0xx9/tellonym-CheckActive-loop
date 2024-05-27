import json
import time
import requests
from threading import Thread, Event, Lock
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

TELEGRAM_BOT_TOKEN = 'TOKEN!!'

class LordGivt:
    def __init__(self):
        self.active_checks = {}
        self.lock = Lock()
        self.bot_thread = Thread(target=self.listen_for_commands)
        self.bot_thread.start()
        self.send_message_to_all("Welcome! This bot has been programmed by @_0x0\n Basecaliy you cannot chack more then 3 account in the sametime \n for using \n /start <username> to begin checking and /stop <username> to stop checking.")

    def select_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('disable-infobars')
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

        return webdriver.Chrome(options=chrome_options)

    def check_loop(self, chat_id, username):
        check_event = self.active_checks[chat_id][username]['event']
        while check_event.is_set():
            self.active_checks[chat_id][username]['attempts'] += 1
            try:
                self.driver = self.select_driver()
                self.driver.get(f"https://api.tellonym.me/profiles/name/{username}?previousRouteName=ScreenProfileSharing&isClickedInSearch=true&sourceElement=Search%20Result&adExpId=91&limit=16")
                time.sleep(2)  # Ensure the page loads

                response = self.driver.find_element(By.TAG_NAME, "pre")
                response_text = response.text
               

                if "The entry you were looking for could not be found." in response_text:
                    self.send_message(chat_id, "[X] Error : User Not Found")
                    break
                elif "This account is banned." in response_text:
                    self.send_message(chat_id, "[X] Error : This account is banned.")
                    break
                else:
                    json_data = json.loads(response_text)
                    isActive = json_data.get("isActive", False)
                    if isActive:
                        self.send_to_telegram(chat_id, json_data)
                        self.active_checks[chat_id][username]['successes'] += 1

                    time.sleep(1)

            except Exception as e:
                print('error')
              
                break
            finally:
                if self.driver:
                    self.driver.quit()

            # Update status message every second
            self.update_status_message(chat_id, username)
            time.sleep(1)  # Ensure the update happens every second

        with self.lock:
            del self.active_checks[chat_id][username]

    def send_to_telegram(self, chat_id, json_data):
        try:
            username = json_data.get("username", "Unknown")
            name = json_data.get("displayName", "Unknown")
            aboutMe = json_data.get("aboutMe", "Unknown")
            following = json_data.get("followingCount", "Unknown")
            followers = json_data.get("followerCount", "Unknown")
            isActive = json_data.get("isActive", "Unknown")

            message = f"""
            [+] {username} is online 

            Name: {name}
            Bio: {aboutMe}
            Following: {following}
            Followers: {followers}
            Active: {'Yes' if isActive else 'No'}
            """
            telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            requests.post(telegram_api_url, data=payload)
            time.sleep(1200)  # Sleep for 20 minutes
        except Exception as e:
            self.send_message(chat_id, f"[X] Error sending message to Telegram -> {str(e)}")

    def send_message(self, chat_id, message):
        telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(telegram_api_url, data=payload)
        if response.status_code == 200:
            message_data = response.json()
            return message_data.get("result", {}).get("message_id")
        return None

    def send_message_to_all(self, message):
        # Send the welcome message to the predefined chat IDs
        for chat_id in self.active_checks:
            self.send_message(chat_id, message)

    def update_status_message(self, chat_id, username):
        message_id = self.active_checks[chat_id][username].get('message_id')
        if message_id:
            status_message = f"Checking @{username}\nAttempts: {self.active_checks[chat_id][username]['attempts']}\nSuccesses: {self.active_checks[chat_id][username]['successes']}"
            telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": status_message,
                "parse_mode": "Markdown"
            }
            requests.post(telegram_api_url, data=payload)

    def start_checking(self, chat_id, username):
        with self.lock:
            if chat_id not in self.active_checks:
                self.active_checks[chat_id] = {}

            if len(self.active_checks[chat_id]) >= 3:
                self.send_message(chat_id, "[!] You can only check up to 3 accounts simultaneously.")
                return

            if username in self.active_checks[chat_id]:
                self.send_message(chat_id, f"[!] Already checking @{username}")
                return

            check_event = Event()
            check_event.set()
            self.active_checks[chat_id][username] = {
                'thread': None,
                'attempts': 0,
                'successes': 0,
                'message_id': None,
                'event': check_event
            }

            self.active_checks[chat_id][username]['thread'] = Thread(target=self.check_loop, args=(chat_id, username))
            self.active_checks[chat_id][username]['thread'].start()
            message_id = self.send_message(chat_id, f"[+] Started checking @{username}")
            self.active_checks[chat_id][username]['message_id'] = message_id
            time.sleep(1)
            self.update_status_message(chat_id, username)

    def stop_checking(self, chat_id, username):
        with self.lock:
            if chat_id in self.active_checks and username in self.active_checks[chat_id]:
                self.active_checks[chat_id][username]['event'].clear()
                self.active_checks[chat_id][username]['thread'].join()
                del self.active_checks[chat_id][username]
                self.send_message(chat_id, f"[+] Stopped checking @{username}")
            else:
                self.send_message(chat_id, f"[!] No checking in progress for @{username}")

    def listen_for_commands(self):
        telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        offset = 0

        while True:
            response = requests.get(telegram_api_url, params={"offset": offset, "timeout": 100})
            if response.status_code == 200:
                updates = response.json().get("result", [])
                for update in updates:
                    offset = update["update_id"] + 1
                    message = update.get("message")
                    if message:
                        chat_id = message["chat"]["id"]
                        text = message.get("text", "").strip().lower()
                        if text.startswith("/start"):
                            parts = text.split(" ")
                            if len(parts) == 2:
                                username = parts[1]
                                self.start_checking(chat_id, username)
                            else:
                                self.send_message(chat_id, "[!] Usage: /start <username>")
                        elif text.startswith("/stop"):
                            parts = text.split(" ")
                            if len(parts) == 2:
                                username = parts[1]
                                self.stop_checking(chat_id, username)
                            else:
                                self.send_message(chat_id, "[!] Usage: /stop <username>")
                        else:
                            self.send_message(chat_id, "[!] Unknown command. Use /start <username> to begin checking or /stop <username> to end.")

if __name__ == "__main__":
    LordGivt()
