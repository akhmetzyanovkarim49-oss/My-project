import sys
import os
import json
import requests
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QComboBox, QMessageBox
)
from PyQt6.QtCore import QThread, pyqtSignal

# Файл для сохранения настроек на устройстве
CONFIG_FILE = "config.json"

# Список доступных бесплатных моделей
FREE_MODELS = {
    "Авто-выбор (OpenRouter Free)": "openrouter/free",
    "Qwen 2.5 Coder 32B (Для кода)": "qwen/qwen-2.5-coder-32b-instruct:free",
    "DeepSeek R1 (Рассуждения)": "deepseek/deepseek-r1:free",
    "Llama 3.3 70B (Универсальная)": "meta-llama/llama-3.3-70b-instruct:free"
}

class AIWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, api_key, model_id, prompt):
        super().__init__()
        self.api_key = api_key
        self.model_id = model_id
        self.prompt = prompt

    def run(self):
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": "Ты полезный и умный ИИ-ассистент."},
                {"role": "user", "content": self.prompt}
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                text = result['choices'][0]['message']['content']
                self.finished.emit(text)
            else:
                self.finished.emit(f"Ошибка {response.status_code}: {response.text}")
        except Exception as e:
            self.finished.emit(f"Ошибка сети: {str(e)}")


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.load_settings()

    def initUI(self):
        self.setWindowTitle('AI Assistant')
        self.resize(500, 650)

        layout = QVBoxLayout()

        # Поле ввода API-ключа
        layout.addWidget(QLabel("<b>API Ключ OpenRouter:</b>"))
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("sk-or-v1-...")
        layout.addWidget(self.key_input)

        # Выбор модели
        layout.addWidget(QLabel("<b>Выберите модель:</b>"))
        self.model_combo = QComboBox()
        for name in FREE_MODELS.keys():
            self.model_combo.addItem(name)
        layout.addWidget(self.model_combo)

        # Кнопка сохранения настроек
        self.save_btn = QPushButton("Сохранить настройки")
        self.save_btn.clicked.connect(self.save_settings_msg)
        layout.addWidget(self.save_btn)

        # Чат
        layout.addWidget(QLabel("<b>Чат:</b>"))
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        layout.addWidget(self.chat_history)

        # Ввод сообщения
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Введите ваш запрос...")
        self.input_field.returnPressed.connect(self.send_message)
        layout.addWidget(self.input_field)

        self.send_btn = QPushButton("Отправить")
        self.send_btn.clicked.connect(self.send_message)
        layout.addWidget(self.send_btn)

        self.setLayout(layout)

    def load_settings(self):
        """Загрузка сохраненного ключа и модели из JSON"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.key_input.setText(config.get("api_key", ""))
                    saved_model_idx = config.get("model_index", 0)
                    self.model_combo.setCurrentIndex(saved_model_idx)
            except Exception:
                pass

    def save_settings(self):
        """Сохранение настроек в JSON"""
        config = {
            "api_key": self.key_input.text().strip(),
            "model_index": self.model_combo.currentIndex()
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    def save_settings_msg(self):
        self.save_settings()
        QMessageBox.information(self, "Успех", "Настройки успешно сохранены!")

    def send_message(self):
        api_key = self.key_input.text().strip()
        text = self.input_field.text().strip()

        if not api_key:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, введите API-ключ!")
            return

        if not text:
            return

        # Автоматически сохраняем настройки при отправке
        self.save_settings()

        # Получаем системный ID выбранной модели
        model_name = self.model_combo.currentText()
        model_id = FREE_MODELS[model_name]

        self.chat_history.append(f"<b>Вы:</b> {text}")
        self.input_field.clear()
        self.send_btn.setEnabled(False)

        # Запуск фонового запроса
        self.worker = AIWorker(api_key, model_id, text)
        self.worker.finished.connect(self.on_ai_response)
        self.worker.start()

    def on_ai_response(self, response_text):
        self.chat_history.append(f"<b>ИИ:</b> {response_text}\n")
        self.send_btn.setEnabled(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    ex.show()
    sys.exit(app.exec())
