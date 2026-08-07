import sys
import requests
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# 🔑 Твой ключ от OpenRouter (вставь сюда свой sk-or-v1-...)
OPENROUTER_API_KEY = "ТВОЙ_OPENROUTER_KEY"

class AIWorker(QThread):
    """Отдельный поток, чтобы интерфейс не зависал во время ответа ИИ"""
    finished = pyqtSignal(str)

    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt

    def run(self):
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "openrouter/free",  # Автоматический выбор бесплатной модели
            "messages": [
                {"role": "system", "content": "Ты полезный ИИ-ассистент."},
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

    def initUI(self):
        self.setWindowTitle('AI Assistant Free')
        self.resize(500, 600)

        layout = QVBoxLayout()

        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        layout.addWidget(self.chat_history)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Введите запрос...")
        self.input_field.returnPressed.connect(self.send_message)
        layout.addWidget(self.input_field)

        self.send_btn = QPushButton("Отправить")
        self.send_btn.clicked.connect(self.send_message)
        layout.addWidget(self.send_btn)

        self.setLayout(layout)

    def send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return

        self.chat_history.append(f"<b>Вы:</b> {text}")
        self.input_field.clear()
        self.send_btn.setEnabled(False)

        # Запуск запроса в фоновом потоке
        self.worker = AIWorker(text)
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
