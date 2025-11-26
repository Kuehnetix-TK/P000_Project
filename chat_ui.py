import customtkinter as ctk
import tkinter as tk
from tkinter import scrolledtext
from sql_engine import SQLBot


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class ChatBotUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Chat SQL Assistant")
        self.geometry("900x600")
        self.minsize(800, 500)

        # SQL Engine laden
        self.sql_bot = SQLBot("C:\Users\baerc\mini-interact\credit\credit.sqlite")

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_header()
        self.create_chat_frame()
        self.create_input_bar()

    # -------------------------------------------------------------
    def create_header(self):
        header = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="transparent")
        header.grid(row=0, column=0, sticky="new", padx=20, pady=10)

        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        title = ctk.CTkLabel(
            header,
            text="Chat SQL Assistant",
            font=ctk.CTkFont(size=26, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w")

        settings_btn = ctk.CTkButton(
            header,
            text="⚙️",
            width=40,
            fg_color="#1f2933",
            hover_color="#111827"
        )
        settings_btn.grid(row=0, column=1, padx=10)

    # -------------------------------------------------------------
    def create_chat_frame(self):
        self.chat_frame = ctk.CTkFrame(self, corner_radius=10)
        self.chat_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))

        self.chat_frame.grid_columnconfigure(0, weight=1)
        self.chat_frame.grid_rowconfigure(0, weight=1)

        self.chat_box = scrolledtext.ScrolledText(
            self.chat_frame,
            wrap=tk.WORD,
            font=("Helvetica", 14),
            bg="#0f172a",
            fg="white",
            insertbackground="white",
            relief="flat"
        )
        self.chat_box.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.chat_box.configure(state="disabled")

    # -------------------------------------------------------------
    def create_input_bar(self):
        input_bar = ctk.CTkFrame(self, height=60, corner_radius=10)
        input_bar.grid(row=2, column=0, sticky="ew", padx=20, pady=10)

        input_bar.grid_columnconfigure(0, weight=1)
        input_bar.grid_columnconfigure(1, weight=0)
        input_bar.grid_columnconfigure(2, weight=0)

        self.entry = ctk.CTkEntry(
            input_bar,
            placeholder_text="Schreibe eine Nachricht oder SQL-Abfrage...",
            height=45
        )
        self.entry.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        speech_btn = ctk.CTkButton(
            input_bar,
            width=50,
            text="🎤",
            fg_color="#1f2933",
            hover_color="#111827",
            command=self.speech_stub
        )
        speech_btn.grid(row=0, column=1, padx=5)

        send_btn = ctk.CTkButton(
            input_bar,
            text="➤",
            width=50,
            fg_color="#1d4ed8",
            command=self.send_message
        )
        send_btn.grid(row=0, column=2, padx=5)

    # -------------------------------------------------------------
    def speech_stub(self):
        self.add_message("🎤 System", "Speech-to-Text aktiviert (noch nicht angebunden).")

    # -------------------------------------------------------------
    def send_message(self):
        user_text = self.entry.get().strip()
        if user_text == "":
            return

        self.add_message("🧑 Du", user_text)
        self.entry.delete(0, tk.END)

        # SQL Verarbeitung
        bot_answer = self.sql_bot.handle_message(user_text)
        self.add_message("🤖 Bot", bot_answer)

    # -------------------------------------------------------------
    def add_message(self, sender, text):
        self.chat_box.configure(state="normal")
        self.chat_box.insert(tk.END, f"{sender}:\n", "sender")
        self.chat_box.insert(tk.END, f"{text}\n\n")
        self.chat_box.configure(state="disabled")
        self.chat_box.yview(tk.END)


# -------------------------------------------------------------
if __name__ == "__main__":
    app = ChatBotUI()
    app.mainloop()
