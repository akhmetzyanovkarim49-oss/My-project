import os
import json
import requests
from threading import Thread

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock

CONFIG_FILE = "config.json"

FREE_MODELS = {
    "Авто-выбор (OpenRouter Free)": "openrouter/free",
    "Qwen 2.5 Coder 32B (Для кода)": "qwen/qwen-2.5-coder-32b-instruct:free",
    "DeepSeek R1 (Рассуждения)": "deepseek/deepseek-r1:free",
    "Llama 3.3 70B (Универсальная)": "meta-llama/llama-3.3-70b-instruct:free"
}

class MainWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=8, **kwargs)
        
        # Поле ключа
        self.add_widget(Label(text="[b]API Ключ OpenRouter:[/b]", markup=True, size_hint_y=None, height=30))
        self.key_input = TextInput(password=True, multiline=False, size_hint_y=None, height=40)
        self.add_widget(self.key_input)
        
        # Выбор модели
        self.add_widget(Label(text="[b]Модель:[/b]", markup=True, size_hint_y=None, height=30))
        self.model_spinner = Spinner(
            text=list(FREE_MODELS.keys())[0],
            values=list(FREE_MODELS.keys()),
            size_hint_y=None,
            height=40
        )
        self.add_widget(self.model_spinner)
        
        # Чат
        self.add_widget(Label(text="[b]Чат:[/b]", markup=True, size_hint_y=None, height=30))
        self.chat_history = TextInput(readonly=True, multiline=True)
        self.add_widget(self.chat_history)
        
        # Ввод сообщения
        self.input_field = TextInput(multiline=False, size_hint_y=None, height=40)
        self.add_widget(self.input_field)
        
        # Кнопка отправки
        self.send_btn = Button(text="Отправить", size_hint_y=None, height=45)
        self.send_btn.bind(on_release=self.send_message)
        self.add_widget(self.send_btn)

        self.load_settings()

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.key_input.text = config.get("api_key", "")
                    saved_model = config.get("model_name")
                    if saved_model in FREE_MODELS:
                        self.model_spinner.text = saved_model
            except Exception:
                pass

    def save_settings(self):
        config = {
            "api_key": self.key_input.text.strip(),
            "model_name": self.model_spinner.text
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    def send_message(self, instance):
        api_key = self.key_input.text.strip()
        text = self.input_field.text.strip()
        
        if not api_key or not text:
            return

        self.save_settings()
        
        model_id = FREE_MODELS[self.model_spinner.text]
        self.chat_history.text += f"\nВы: {text}"
        self.input_field.text = ""
        self.send_btn.disabled = True

        Thread(target=self.make_request, args=(api_key, model_id, text)).start()

    def make_request(self, api_key, model_id, prompt):
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        try:
            res = requests.post(url, headers=headers, json=data, timeout=30)
            if res.status_code == 200:
                answer = res.json()['choices'][0]['message']['content']
            else:
                answer = f"Ошибка: {res.status_code}"
        except Exception as e:
            answer = f"Ошибка сети: {str(e)}"

        Clock.schedule_once(lambda dt: self.update_chat(answer))

    def update_chat(self, text):
        self.chat_history.text += f"\nИИ: {text}\n"
        self.send_btn.disabled = False

class AIApp(App):
    def build(self):
        return MainWidget()

if __name__ == '__main__':
    AIApp().run()
