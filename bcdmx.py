import tkinter as tk
from tkinter import scrolledtext, font
import asyncio
import aiohttp
import random
import json
from threading import Thread
import pyttsx3
import os
from vosk import Model, KaldiRecognizer
import pyaudio
import wave
import json

api_keys = [
    "sk-6fb424eb7c974078344fa97cafe3455c",
    "sk-9e03284794de52386d03a648211c5265",
    "sk-ecf35c06119db50b23bc92c09bf827d3",
    "sk-8b97d22d5f8f7aa399068a6ebbfdff44",
    "sk-37889f53af5462b8c50b21c8dc1bfea24"
]
url = "https://api.baichuan-ai.com/v1/chat/completions"


async def send_request(api_key, user_input):
    data = {
        "model": "Baichuan2-Turbo",
        "messages": [{"role": "user", "content": user_input}],
        "stream": False,
        "temperature": 0.3,
        "top_p": 0.85,
        "top_k": 5,
        "with_search_enhance": False
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                choices = result.get("choices", [])
                return choices
            else:
                return [{"message": {"content": f"请求失败，状态码: {response.status}"}}]


class QAWindow:
    def __init__(self, master):
        self.master = master
        master.title("智能问答")
        master.geometry("600x400")

        default_font = font.nametofont("TkDefaultFont")
        larger_font = default_font.copy()
        larger_font.config(size=default_font.cget("size") + 2)

        self.answer_box = scrolledtext.ScrolledText(master, font=larger_font, wrap=tk.WORD, height=15)
        self.answer_box.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        self.input_frame = tk.Frame(master)
        self.input_frame.pack(fill=tk.X, padx=10, pady=5)

        # 语音输入按钮
        self.voice_input_button = tk.Button(self.input_frame, text="语音输入", command=self.handle_voice_input,
                                            font=larger_font)
        self.voice_input_button.pack(side=tk.RIGHT, padx=10)

        self.question_entry = tk.Entry(self.input_frame, font=larger_font, fg="grey")
        self.question_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.placeholder_text = "请输入问题："
        self.question_entry.insert(0, self.placeholder_text)
        self.question_entry.bind("<FocusIn>", self.on_focus_in)
        self.question_entry.bind("<FocusOut>", self.on_focus_out)

        self.ask_button = tk.Button(self.input_frame, text="提问", command=self.handle_question, font=larger_font)
        self.ask_button.pack(side=tk.LEFT, padx=10)

        master.bind('<Return>', lambda event=None: self.ask_button.invoke())
        master.bind('<Escape>', lambda event=None: master.destroy())

        # 右键菜单
        self.right_click_menu = tk.Menu(master, tearoff=0)
        self.right_click_menu.add_command(label="复制", command=self.copy_text)
        self.right_click_menu.add_command(label="粘贴", command=self.paste_text)
        self.right_click_menu.add_command(label="朗读", command=self.speak_text)

        self.answer_box.bind("<Button-3>", self.show_right_click_menu)
        self.question_entry.bind("<Button-3>", self.show_right_click_menu)

    def handle_voice_input(self):
        model_path = "E:\\Fox\\vosk-model-small-cn-0.22"
        if not os.path.exists(model_path):
            print("模型路径不存在，请检查！")
            return

        model = Model(model_path)
        rec = KaldiRecognizer(model, 16000)
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=4096)
        stream.start_stream()

        print("请说话...")
        data = bytearray()
        for i in range(0, int(16000 / 4096 * 5)):
            data.extend(stream.read(4096))
        stream.stop_stream()
        stream.close()
        p.terminate()

        data_bytes = bytes(data)
        if rec.AcceptWaveform(data_bytes):
            result = json.loads(rec.Result())
            text = result.get("text", "")
            print("您说：", text)

            # 移除识别结果中的所有空格
            text_no_spaces = text.replace(" ", "")

            self.question_entry.delete(0, tk.END)
            self.question_entry.insert(0, text_no_spaces)  # 使用去除空格后的文本
            self.question_entry.config(fg="black")
        else:
            print("无法识别语音，请再试一次。")

    def on_focus_in(self, event):
        if self.question_entry.get() == self.placeholder_text:
            self.question_entry.delete(0, tk.END)
            self.question_entry.config(fg="black")

    def on_focus_out(self, event):
        if not self.question_entry.get():
            self.question_entry.insert(0, self.placeholder_text)
            self.question_entry.config(fg="grey")

    def handle_question(self):
        question = self.question_entry.get()
        if question != self.placeholder_text:
            self.answer_box.config(state=tk.NORMAL)
            if not self.answer_box.get("end-2c") == "\n":
                self.answer_box.insert(tk.END, "\n")
            self.answer_box.insert(tk.END, f"Q: {question}\n")
            self.answer_box.config(state=tk.DISABLED)
            self.fetch_answer(question)
            self.question_entry.delete(0, tk.END)

    async def async_fetch_answer(self, api_key, question):
        choices = await send_request(api_key, question)
        if choices:
            answer = choices[0].get("message", {}).get("content", "无回答")
            self.answer_box.config(state=tk.NORMAL)
            self.answer_box.insert(tk.END, f"A: {answer}\n\n")
            self.answer_box.config(state=tk.DISABLED)
            self.answer_box.yview(tk.END)

    def fetch_answer(self, question):
        selected_api_key = random.choice(api_keys)

        def update_answer():
            asyncio.run_coroutine_threadsafe(self.async_fetch_answer(selected_api_key, question), loop)

        self.master.after(0, update_answer)

    def copy_text(self):
        try:
            self.master.clipboard_clear()
            text = self.master.focus_get().get(tk.SEL_FIRST, tk.SEL_LAST)
            self.master.clipboard_append(text)
        except tk.TclError:
            pass

    def paste_text(self):
        try:
            text = self.master.clipboard_get()
            self.master.focus_get().insert(tk.INSERT, text)
        except tk.TclError:
            pass

    def speak_text(self):
        try:
            text = self.master.focus_get().get(tk.SEL_FIRST, tk.SEL_LAST)
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except tk.TclError:
            pass

    def show_right_click_menu(self, event):
        try:
            self.right_click_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.right_click_menu.grab_release()


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


def run_event_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


thread = Thread(target=run_event_loop, args=(loop,))
thread.start()

root = tk.Tk()
qa_window = QAWindow(root)
root.mainloop()

loop.call_soon_threadsafe(loop.stop)
thread.join()