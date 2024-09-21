import os
import subprocess
import json
import requests
import shutil

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QMessageBox, QDialog, QFileDialog
from uuid import uuid1
import minecraft_launcher_lib

file_game = os.path.expanduser("~/AppData/Roaming/.minecraft")
photo_launcher = os.path.join(file_game, "textures")
game_version = os.path.join(file_game, "versions")
settings_file = os.path.join(file_game, "launcher_settings.json")
microsoft_account_file = os.path.join(file_game, "Microsoftakk.json")

class LaunchThread(QtCore.QThread):
    launcher_setup_signal = QtCore.pyqtSignal(str, str)
    progress_updata_signal = QtCore.pyqtSignal(int, int, str)
    state_updata_signal = QtCore.pyqtSignal(bool)

    version_id = ''
    username = ''

    progress = 0
    progress_max = 0
    progress_label = '' 

    def __init__(self, minecraft_folder):
        super().__init__()
        self.minecraft_folder = minecraft_folder
        self.launcher_setup_signal.connect(self.launch_setup)

    def launch_setup(self, version_id, username):
        self.version_id = version_id
        self.username = username 

    def updata_progress_label(self, value):
        self.progress_label = value
        self.progress_updata_signal.emit(self.progress, self.progress_max, self.progress_label)
    def updata_progress(self, value):
        self.progress = value
        self.progress_updata_signal.emit(self.progress, self.progress_max, self.progress_label)
    def updata_progress_max(self, value):
        self.progress_max = value
        self.progress_updata_signal.emit(self.progress, self.progress_max, self.progress_label)
    
    def run(self):
        self.state_updata_signal.emit(True)

        minecraft_launcher_lib.install.install_minecraft_version(versionid=self.version_id, minecraft_directory=self.minecraft_folder, callback={ 'setStatus': self.updata_progress_label, 'setProgress': self.updata_progress, 'setMax': self.updata_progress_max})
        
        # Чтение учетных данных из файла
        microsoft_account_file = os.path.join(self.minecraft_folder, "Microsoftakk.json")
        if os.path.exists(microsoft_account_file) and os.path.getsize(microsoft_account_file) > 0:
            with open(microsoft_account_file, 'r') as f:
                file_content = f.read()
                print(f"File content: {file_content}")  # Print the file content for debugging
                try:
                    credentials = json.loads(file_content)
                    email = credentials.get('email')
                    password = credentials.get('password')
                    print(f"Loaded credentials: email={email}, password={password}")  # Print loaded credentials
                except json.JSONDecodeError:
                    print("Error: The file does not contain valid JSON.")
                    self.state_updata_signal.emit(False)
                    return
        else:
            print("Error: The file does not exist or is empty.")
            self.state_updata_signal.emit(False)
            return

        # Аутентификация через OAuth 2.0
        token = self.authenticate_microsoft(email, password)
        if not token:
            self.state_updata_signal.emit(False)
            return

        options = {
            'username': self.username,
            'uuid': str(uuid1()),
            'token': token  # Используем токен доступа
        }

        # Проверяем и создаем папку config, если она не существует
        config_path = os.path.join(self.minecraft_folder, "config")
        if not os.path.exists(config_path):
            os.makedirs(config_path)

        # Проверяем и создаем папку logs, если она не существует
        logs_path = os.path.join(self.minecraft_folder, "logs")
        if not os.path.exists(logs_path):
            os.makedirs(logs_path)

        # Создаем файл лога
        log_file_path = os.path.join(logs_path, "minecraft_launcher.log")
        with open(log_file_path, "w") as log_file:
            command = minecraft_launcher_lib.command.get_minecraft_command(version=self.version_id, minecraft_directory=self.minecraft_folder, options=options)

            # Объединяем моды из выбранных папок
            mods_path = os.path.join(self.minecraft_folder, "mods")
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    settings = json.load(f)
                    mods_folders = settings.get('mods_folders', [])
                    for folder in mods_folders:
                        for mod_file in os.listdir(folder):
                            shutil.copy(os.path.join(folder, mod_file), mods_path)

            subprocess.call(command, stdout=log_file, stderr=subprocess.STDOUT)

        self.state_updata_signal.emit(False)

    def authenticate_microsoft(self, email, password):
        # Здесь должен быть код для аутентификации через OAuth 2.0
        # Этот код зависит от конкретного API Microsoft, который вы используете
        # В данном примере используется заглушка
        # Вам нужно будет реализовать реальный процесс аутентификации
        # и получить токен доступа
        return "your_access_token_here"

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(300, 400)
        icon_path = os.path.join(photo_launcher, "sitting.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))
        layout = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel("Выбери версии:", self)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        self.beta_checkbox = QtWidgets.QCheckBox("Beta", self)
        self.beta_checkbox.setChecked(True)
        layout.addWidget(self.beta_checkbox)

        self.snapshot_checkbox = QtWidgets.QCheckBox("Снэпшоты", self)
        self.snapshot_checkbox.setChecked(True)
        layout.addWidget(self.snapshot_checkbox)

        self.installed_checkbox = QtWidgets.QCheckBox("Установленные", self)
        self.installed_checkbox.setChecked(False)
        layout.addWidget(self.installed_checkbox)

        # Добавляем поле для выбора папки
        self.folder_label = QtWidgets.QLabel("Путь к папке .minecraft:", self)
        layout.addWidget(self.folder_label)

        self.folder_path = QtWidgets.QLineEdit(self)
        self.folder_path.setReadOnly(True)
        layout.addWidget(self.folder_path)

        self.select_folder_button = QtWidgets.QPushButton("Выбрать папку", self)
        self.select_folder_button.clicked.connect(self.select_folder)
        layout.addWidget(self.select_folder_button)

        self.load_settings()

    def load_settings(self):
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                self.beta_checkbox.setChecked(settings.get('beta', True))
                self.snapshot_checkbox.setChecked(settings.get('snapshot', True))
                self.installed_checkbox.setChecked(settings.get('installed', False))
                self.folder_path.setText(settings.get('minecraft_folder', file_game))

    def save_settings(self):
        settings = {
            'beta': self.beta_checkbox.isChecked(),
            'snapshot': self.snapshot_checkbox.isChecked(),
            'installed': self.installed_checkbox.isChecked(),
            'minecraft_folder': self.folder_path.text()
        }
        with open(settings_file, 'w') as f:
            json.dump(settings, f)

    def closeEvent(self, event):
        self.save_settings()
        event.accept()

    def select_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Выберите папку .minecraft")
        if folder:
            self.folder_path.setText(folder)
            self.save_settings()

class ModsFolderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Mods Folders")
        self.setFixedSize(400, 300)
        icon_path = os.path.join(photo_launcher, "papka.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))
        layout = QtWidgets.QVBoxLayout(self)

        self.folder_list = QtWidgets.QListWidget(self)
        layout.addWidget(self.folder_list)

        self.add_button = QtWidgets.QPushButton("Add Folder", self)
        self.add_button.clicked.connect(self.add_folder)
        layout.addWidget(self.add_button)

        self.remove_button = QtWidgets.QPushButton("Remove Selected", self)
        self.remove_button.clicked.connect(self.remove_folder)
        layout.addWidget(self.remove_button)

        self.load_folders()

    def add_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Mods Folder")
        if folder:
            self.folder_list.addItem(folder)
            self.save_folders()

    def remove_folder(self):
        selected_items = self.folder_list.selectedItems()
        for item in selected_items:
            self.folder_list.takeItem(self.folder_list.row(item))
        self.save_folders()

    def load_folders(self):
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                folders = settings.get('mods_folders', [])
                for folder in folders:
                    self.folder_list.addItem(folder)

    def save_folders(self):
        folders = [self.folder_list.item(i).text() for i in range(self.folder_list.count())]
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        settings['mods_folders'] = folders
        with open(settings_file, 'w') as f:
            json.dump(settings, f)

    def get_selected_folders(self):
        return [self.folder_list.item(i).text() for i in range(self.folder_list.count())]

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(505, 457)
        MainWindow.setFixedSize(505, 457)  # Запрет на изменение размера окна
        # Установка иконки окна
        icon_path = os.path.join(photo_launcher, "icon.png")
        if os.path.exists(icon_path):
            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap(icon_path), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
            MainWindow.setWindowIcon(icon)

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.centralwidget.setStyleSheet("background-color: #333333;")  # Темный фон
        self.gridLayout_2 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        spacerItem = QtWidgets.QSpacerItem(0, 15, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        self.gridLayout.addItem(spacerItem, 9, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Expanding)
        self.gridLayout.addItem(spacerItem1, 1, 0, 1, 1)
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setMaximumSize(QtCore.QSize(500, 150))
        self.label.setText("")
        logo_path = os.path.join(photo_launcher, "Logo.png")
        if os.path.exists(logo_path):
            self.label.setPixmap(QtGui.QPixmap(logo_path))
        self.label.setScaledContents(True)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setMaximumSize(QtCore.QSize(100, 25))
        self.label_2.setObjectName("label_2")
        self.label_2.setStyleSheet("color: #FFFFFF;")  # Белый текст
        self.label_2.setText("Видите ник :")
        self.gridLayout.addWidget(self.label_2, 2, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.start_progress = QtWidgets.QProgressDialog(self.centralwidget)
        self.start_progress.setProperty("value", 24)
        self.start_progress.setObjectName("progressBar")
        self.start_progress.setVisible(False)
        self.start_progress.setStyleSheet("background-color: #444444; color: #FFFFFF;")  # Темный фон и белый текст
        self.gridLayout.addWidget(self.start_progress, 8, 0, 1, 1)
        self.version_select = QtWidgets.QComboBox(self.centralwidget)
        self.version_select.setMinimumSize(QtCore.QSize(100, 25))
        self.version_select.setMaximumSize(QtCore.QSize(100, 25))
        self.version_select.setObjectName("version_select")

        self.load_minecraft_folder()  # Загружаем папку перед обновлением списка версий
        self.update_version_list()

        self.version_select.setStyleSheet("background-color: #555555; color: #FFFFFF;")  # Темный фон и белый текст
        self.gridLayout.addWidget(self.version_select, 6, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignHCenter)
        spacerItem2 = QtWidgets.QSpacerItem(10, 20, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        self.gridLayout.addItem(spacerItem2, 4, 0, 1, 1)
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setMinimumSize(QtCore.QSize(100, 25))
        self.label_3.setMaximumSize(QtCore.QSize(100, 25))
        self.label_3.setObjectName("version_select")
        self.label_3.setStyleSheet("color: #FFFFFF;")  # Белый текст
        self.label_3.setText("Выберите Версию :")
        self.gridLayout.addWidget(self.label_3, 5, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.username = QtWidgets.QLineEdit(self.centralwidget)
        self.username.setMaximumSize(QtCore.QSize(100, 25))
        self.username.setObjectName("lineEdit")
        self.username.setStyleSheet("background-color: #555555; color: #FFFFFF;")  # Темный фон и белый текст
        self.gridLayout.addWidget(self.username, 3, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignHCenter)
        self.start_button = QtWidgets.QPushButton(self.centralwidget)
        self.start_button.setMaximumSize(QtCore.QSize(100, 25))
        self.start_button.setObjectName("start_button")
        self.start_button.setStyleSheet("background-color: #555555; color: #FFFFFF;")  # Темный фон и белый текст
        self.start_button.setText("Play")
        self.start_button.clicked.connect(self.launch_game)

        # Добавляем кнопку настроек в нижний левый угол
        self.settings_button = QtWidgets.QPushButton(self.centralwidget)
        self.settings_button.setMaximumSize(QtCore.QSize(100, 25))
        self.settings_button.setObjectName("settings_button")
        self.settings_button.setStyleSheet("background-color: #555555; color: #FFFFFF;")  # Темный фон и белый текст
        self.settings_button.setText("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        self.gridLayout.addWidget(self.settings_button, 11, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignLeft)

        # Добавляем кнопку для выбора папок с модами
        self.mods_button = QtWidgets.QPushButton(self.centralwidget)
        self.mods_button.setMaximumSize(QtCore.QSize(100, 25))
        self.mods_button.setObjectName("mods_button")
        self.mods_button.setStyleSheet("background-color: #555555; color: #FFFFFF;")  # Темный фон и белый текст
        self.mods_button.setText("Mods Folders")
        self.mods_button.clicked.connect(self.open_mods_folders)
        self.gridLayout.addWidget(self.mods_button, 12, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignLeft)

        # Добавляем кнопку для открытия папки .minecraft
        self.open_minecraft_folder_button = QtWidgets.QPushButton(self.centralwidget)
        self.open_minecraft_folder_button.setMaximumSize(QtCore.QSize(100, 25))
        self.open_minecraft_folder_button.setObjectName("open_minecraft_folder_button")
        self.open_minecraft_folder_button.setStyleSheet("background-color: #555555; color: #FFFFFF;")  # Темный фон и белый текст
        self.open_minecraft_folder_button.setText("Open .minecraft")
        self.open_minecraft_folder_button.clicked.connect(self.open_minecraft_folder)
        self.gridLayout.addWidget(self.open_minecraft_folder_button, 12, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignRight)

        self.gridLayout.addWidget(self.start_button, 10, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignHCenter)
        spacerItem3 = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Fixed)
        self.gridLayout.addItem(spacerItem3, 7, 0, 1, 1)

        self.gridLayout_2.addLayout(self.gridLayout, 1, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)

        self.launch_thread = LaunchThread(self.minecraft_folder)
        self.launch_thread.state_updata_signal.connect(self.state_updata)
        self.launch_thread.progress_updata_signal.connect(self.update_progress)

        MainWindow.setWindowTitle("Minecraft_Launcher")

        QtCore.QMetaObject.connectSlotsByName(MainWindow)
 
    def state_updata(self, value):
        self.start_button.setDisabled(value)
        self.start_progress.setDisabled(not value)
    def update_progress(self, progress, max_progress, label):
        self.start_progress.setValue(progress)
        self.start_progress.setMaximum(max_progress)
        self.start_progress.setLabelText(label)
    def launch_game(self):
        self.launch_thread.launcher_setup_signal.emit(self.version_select.currentText(), self.username.text())
        self.launch_thread.start()

    def update_version_list(self):
        self.version_select.clear()
        versions = minecraft_launcher_lib.utils.get_version_list()
        installed_versions = os.listdir(os.path.join(self.minecraft_folder, "versions"))

        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                beta_enabled = settings.get('beta', True)
                snapshot_enabled = settings.get('snapshot', True)
                installed_enabled = settings.get('installed', False)
        else:
            beta_enabled = True
            snapshot_enabled = True
            installed_enabled = False

        if installed_enabled:
            for version in installed_versions:
                self.version_select.addItem(version)
        else:
            for version in versions:
                if version['type'] == 'release':
                    self.version_select.addItem(version['id'])
                elif version['type'] == 'old_beta' and beta_enabled:
                    self.version_select.addItem(version['id'])
                elif version['type'] == 'old_alpha' and beta_enabled:
                    self.version_select.addItem(version['id'])
                elif version['type'] == 'snapshot' and snapshot_enabled:
                    self.version_select.addItem(version['id'])

    def open_settings(self):
        dialog = SettingsDialog(self.centralwidget)
        dialog.exec()
        self.load_minecraft_folder()
        self.update_version_list()

    def open_mods_folders(self):
        dialog = ModsFolderDialog(self.centralwidget)
        dialog.exec()
        self.update_version_list()

    def open_minecraft_folder(self):
        if os.path.exists(self.minecraft_folder):
            os.startfile(self.minecraft_folder)
        else:
            QMessageBox.warning(self.centralwidget, "Error", "The .minecraft folder does not exist.")

    def load_minecraft_folder(self):
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                settings = json.load(f)
                self.minecraft_folder = settings.get('minecraft_folder', file_game)
        else:
            self.minecraft_folder = file_game

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())