#Made by https://github.com/MIMIC95 feel free to send feedback.
import time
import customtkinter
from PIL import Image, ImageTk
from customtkinter import CTk, CTkImage, CTkLabel

import json
import requests
import os
import concurrent.futures
import tkinter as tk
from tkinter import filedialog
from threading import Event, Thread
import shutil

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("dark-blue")

my_count = 0
data = []
image_files = []
config_file = "config.json"
autoplay_event = Event()

class App(CTk):
    def __init__(self):
        super().__init__()

        self.minsize(800, 600)
        self.title("Gelbooru Image Downloader/Viewer by MIMIC95")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        frame = customtkinter.CTkFrame(master=self)
        frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(master=frame, bd=2, relief="solid", background="dimgray")
        self.canvas.grid(row=0, column=0, columnspan=5, pady=20, padx=20, sticky="nsew")

        self.entry1 = customtkinter.CTkEntry(master=frame, placeholder_text="Tags")
        self.entry1.grid(row=1, column=0, columnspan=5, pady=5, padx=5, sticky="ew")

        self.entry3 = customtkinter.CTkEntry(master=frame, placeholder_text="Gelbooru API Key")
        self.entry3.grid(row=2, column=0, columnspan=5, pady=5, padx=5, sticky="ew")

        self.info_label = customtkinter.CTkLabel(master=frame, text="")
        self.info_label.grid(row=4, column=0, columnspan=5, pady=5, padx=5, sticky="ew")

        self.slider = customtkinter.CTkSlider(master=frame, from_=0.5, to=10, number_of_steps=19, command=self.update_info_label)
        self.slider.set(2.5)
        self.slider.grid(row=3, column=0, columnspan=5, pady=5, padx=5, sticky="ew")

        self.load_config()

        self.canvas.bind("<Double-Button-1>", self.open_image)

        button_prev = customtkinter.CTkButton(master=frame, text="Previous", command=lambda: self.send_request("prev"))
        button_prev.grid(row=5, column=0, pady=5, padx=5, sticky="ew")

        button_search = customtkinter.CTkButton(master=frame, text="Search", command=lambda: self.send_request("search"))
        button_search.grid(row=5, column=1, pady=5, padx=5, sticky="ew")

        button_next = customtkinter.CTkButton(master=frame, text="Next", command=lambda: self.send_request("next"))
        button_next.grid(row=5, column=2, pady=5, padx=5, sticky="ew")

        self.button_autoplay = customtkinter.CTkButton(master=frame, text="Autoplay", command=self.toggle_autoplay)
        self.button_autoplay.grid(row=5, column=3, pady=5, padx=5, sticky="ew")

        button_backup = customtkinter.CTkButton(master=frame, text="BACKUP IMAGES", command=self.backup_images)
        button_backup.grid(row=5, column=4, pady=5, padx=5, sticky="ew")

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=1)
        frame.grid_columnconfigure(3, weight=1)
        frame.grid_columnconfigure(4, weight=1)

    def save_config(self, tags, post_count, api_key):
        config = {
            "tags": tags,
            "post_count": post_count,
            "api_key": api_key
        }
        with open(config_file, 'w') as f:
            json.dump(config, f)

    def load_config(self):
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.entry1.insert(0, config.get("tags", ""))
                self.entry3.insert(0, config.get("api_key", ""))

    def download_image(self, image_url, image_path):
        image_data = requests.get(image_url).content
        with open(image_path, 'wb') as f:
            f.write(image_data)
        print(f"Downloaded: {image_url} to {image_path}")

    def delayed_download(self, image_url, image_path):
        time.sleep(1)
        self.download_image(image_url, image_path)

    def background_download(self, images):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for i, (image_url, image_path) in enumerate(images):
                if i < 10:
                    futures.append(executor.submit(self.download_image, image_url, image_path))
                else:
                    Thread(target=self.delayed_download, args=(image_url, image_path)).start()
            concurrent.futures.wait(futures)
        self.display_image()

    def send_request(self, request_type):
        global my_count, data, image_files
        if request_type == "search":
            tags = self.entry1.get()
            api_key = self.entry3.get()
            post_count = 100
            tags = tags
            self.save_config(tags, post_count, api_key)

            request_url = f"https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1&limit={post_count}&tags={tags}&api_key={api_key}"
            response = requests.get(request_url)

            if response.status_code == 200:
                try:
                    data = response.json()["post"]
                    my_count = 0
                    image_files = []
                    images_dir = os.path.join(os.path.dirname(__file__), "Images")
                    os.makedirs(images_dir, exist_ok=True)
                    images = []
                    for i, post in enumerate(data):
                        image_url = post["file_url"]
                        if image_url.endswith(".mp4"):
                            print("Skipping: " + image_url)
                            continue
                        image_name = f"image_{i}.jpg"
                        image_path = os.path.join(images_dir, image_name)
                        image_files.append(image_path)
                        images.append((image_url, image_path))
                    Thread(target=self.background_download, args=(images,)).start()
                    self.display_image()  
                except json.JSONDecodeError:
                    print("Failed to decode JSON response")
            else:
                print(f"Request failed with status code: {response.status_code}")
        elif request_type == "next":
            self.next_image()
        elif request_type == "prev":
            self.prev_image()
        self.update_info_label()

    def next_image(self):
        global my_count
        while my_count < len(image_files) - 1:
            my_count += 1
            if os.path.exists(image_files[my_count]):
                self.display_image()
                break

    def prev_image(self):
        global my_count
        while my_count > 0:
            my_count -= 1
            if os.path.exists(image_files[my_count]):
                self.display_image()
                break

    def display_image(self):
        global my_count
        if my_count < len(image_files):
            image_path = image_files[my_count]
            if not os.path.exists(image_path):
                print(f"Image not found: {image_path}")
                return
            print("Displaying: " + image_path)
            image = Image.open(image_path)
            self.canvas.delete("all")
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            image_ratio = image.width / image.height
            canvas_ratio = canvas_width / canvas_height

            if image_ratio > canvas_ratio:
                new_width = canvas_width
                new_height = int(canvas_width / image_ratio)
            else:
                new_height = canvas_height
                new_width = int(canvas_height * image_ratio)

            resized_image = image.resize((new_width, new_height), Image.LANCZOS)
            self.tk_image = ImageTk.PhotoImage(resized_image)
            self.canvas.create_image(canvas_width // 2, canvas_height // 2, image=self.tk_image, anchor="center")
            self.update_idletasks()
            self.update_info_label()
            print("> displayed " + str(my_count + 1) + " images out of " + str(len(image_files)))
            time.sleep(0.1)

    def open_image(self, event):
        if my_count < len(image_files):
            image_path = image_files[my_count]
            if os.path.exists(image_path):
                if os.name == 'nt': 
                    os.system(f'start "" "{image_path}"')
                else: 
                    os.system(f'xdg-open "{image_path}"')

    def autoplay(self):
        global my_count
        if autoplay_event.is_set():
            self.next_image()
            delay = int(self.slider.get() * 1000) 
            self.after(delay, self.autoplay) 

    def toggle_autoplay(self):
        if autoplay_event.is_set():
            autoplay_event.clear()
            self.button_autoplay.configure(text="Autoplay")
        else:
            autoplay_event.set()
            self.button_autoplay.configure(text="Stop Autoplay")
            self.autoplay()

    def backup_images(self):
        images_dir = os.path.join(os.path.dirname(__file__), "Images")
        if not os.path.exists(images_dir):
            print("No images to backup.")
            return

        backup_dir = filedialog.askdirectory(title="Select Backup Directory")
        if backup_dir:
            for image_file in os.listdir(images_dir):
                full_file_path = os.path.join(images_dir, image_file)
                if os.path.isfile(full_file_path):
                    shutil.copy(full_file_path, backup_dir)
            print(f"All images have been copied to {backup_dir}")

    def update_info_label(self, *args):
        if my_count < len(image_files):
            image_path = image_files[my_count]
            if os.path.exists(image_path):
                image = Image.open(image_path)
                self.info_label.configure(text=f"Image: {os.path.basename(image_path)} | Size: {image.width}x{image.height} | Delay: {self.slider.get()}s")
            else:
                self.info_label.configure(text=f"Image not found | Delay: {self.slider.get()}s")
        else:
            self.info_label.configure(text=f"Delay: {self.slider.get()}s")

if __name__ == "__main__":
    app = App()
    app.mainloop()