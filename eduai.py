import json
import os
from datetime import datetime
import requests
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.clock import Clock
from io import BytesIO
from PIL import Image as PILImage

USER_DATA_FILE = "user_data.json"
API_URL = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
HEADERS = {"Authorization": "Bearer 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"} # invalid token


def save_user_email(email):
    with open(USER_DATA_FILE, "w") as file:
        json.dump({"email": email}, file)


def load_user_email():
    try:
        with open(USER_DATA_FILE, "r") as file:
            data = json.load(file)
            return data.get("email", "")
    except FileNotFoundError:
        return ""


def get_user_data(user_id):
    file_name = f'{user_id}_data.txt'

    # Check if the file exists
    if os.path.exists(file_name):
        with open(file_name, 'r') as f:
            data = f.readlines()
            worksheets_generated = int(data[0].split(':')[1].strip())
            last_update_date = data[1].split(':')[1].strip()
            return worksheets_generated, last_update_date
    else:
        # Create the file for new user
        with open(file_name, 'w') as f:
            f.write("worksheets_generated: 0\n")
            f.write(f"last_update_date: {datetime.now().strftime('%Y-%m-%d')}\n")
        return 0, datetime.now().strftime('%Y-%m-%d')


def update_user_data(user_id, worksheets_generated, current_date):
    file_name = f'{user_id}_data.txt'

    with open(file_name, 'w') as f:
        f.write(f"worksheets_generated: {worksheets_generated}\n")
        f.write(f"last_update_date: {current_date}\n")


def can_generate_worksheet(user_id):
    # Get user data
    worksheets_generated, last_update_date = get_user_data(user_id)

    # Check if 24 hours have passed since the last generation
    current_date = datetime.now().strftime('%Y-%m-%d')

    # If more than 24 hours have passed, reset the worksheet count
    if last_update_date != current_date:
        worksheets_generated = 0

    if worksheets_generated < 3:
        return True  # User can generate a worksheet
    else:
        return False  # User has reached the limit of 3 worksheets


def generate_worksheet(user_id):
    # Check if user can gemerate a worksheet
    if can_generate_worksheet(user_id):
        worksheets_generated, last_update_date = get_user_data(user_id)
        worksheets_generated += 1
        current_date = datetime.now().strftime('%Y-%m-%d')

        # Update the user's file
        update_user_data(user_id, worksheets_generated, current_date)

        return True  # Worksheet was successfully generated
    else:
        return False  # User has reached the worksheet limit


class StartScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', spacing=20, padding=50)

        self.label = Label(text='Please enter your email:', font_size='20sp')
        self.email_input = TextInput(hint_text='Enter your email', multiline=False)
        layout.add_widget(self.label)
        layout.add_widget(self.email_input)

        student_btn = Button(text="Student", size_hint=(None, None), size=(200, 50))
        teacher_btn = Button(text="Teacher", size_hint=(None, None), size=(200, 50))

        student_btn.bind(on_release=self.go_to_generate_screen_student)
        teacher_btn.bind(on_release=self.go_to_generate_screen_teacher)

        layout.add_widget(student_btn)
        layout.add_widget(teacher_btn)
        self.add_widget(layout)

        Clock.schedule_once(self.load_previous_login, 0)

    def load_previous_login(self, dt):
        email = load_user_email()
        if email:
            self.email_input.text = email
            Clock.schedule_once(lambda dt: self.go_to_generate_screen_student(None), 0)

    def go_to_generate_screen_student(self, instance):
        save_user_email(self.email_input.text)
        self.manager.current = 'generate_student'

    def go_to_generate_screen_teacher(self, instance):
        save_user_email(self.email_input.text)
        self.manager.current = 'generate_teacher'


class GenerateScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', spacing=20, padding=50)

        self.label = Label(text="Enter the subject for the image you want to generate:", font_size='18sp')
        self.subject_input = TextInput(hint_text="Enter the subject", multiline=False)
        self.subject_input.bind(on_text_validate=self.generate_image)

        self.image_label = Label(text="Image will appear here!", font_size='16sp')
        self.generated_image = Image(size_hint=(None, None), size=(300, 300))

        self.image_count_label = Label(text="Images generated: 0", font_size='16sp')
        self.generated_images_count = 0

        generate_btn = Button(text="Generate Image", size_hint=(None, None), size=(200, 50))
        generate_btn.bind(on_release=self.generate_image)

        layout.add_widget(self.label)
        layout.add_widget(self.subject_input)
        layout.add_widget(generate_btn)
        layout.add_widget(self.image_label)
        layout.add_widget(self.generated_image)
        layout.add_widget(self.image_count_label)

        self.add_widget(layout)

    def generate_image(self, instance=None):
        subject = self.subject_input.text.strip()
        if not subject:
            self.image_label.text = "Please enter a subject!"
            return

        prompt = f"Create an image of {subject}"
        image_data = self.get_generated_image(prompt)

        if image_data:
            img = PILImage.open(BytesIO(image_data))
            img.save("generated_image.png")
            self.generated_image.source = "generated_image.png"
            self.image_label.text = "Image generated successfully!"
            self.generated_images_count += 1
            self.image_count_label.text = f"Images generated: {self.generated_images_count}"
        else:
            self.image_label.text = "Error generating image. Please try again!"

    def get_generated_image(self, prompt):
        try:
            response = requests.post(API_URL, headers=HEADERS, json={"inputs": prompt})
            response.raise_for_status()
            data = response.json()
            return data.get("image") if isinstance(data, dict) else None
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            return None


class GenerateStudentScreen(GenerateScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "generate_student"


class GenerateTeacherScreen(GenerateScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "generate_teacher"


class MainApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(StartScreen(name='start'))
        sm.add_widget(GenerateStudentScreen(name='generate_student'))
        sm.add_widget(GenerateTeacherScreen(name='generate_teacher'))
        return sm


if __name__ == '__main__':
    MainApp().run()





