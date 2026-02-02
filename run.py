import subprocess
import os
if __name__ == '__main__':

    venv_path = 'VENV_PATH'

    second_script_path = r"SCRIPT_PATH" # path to main.py

    command = [
        os.path.join(venv_path, 'Scripts', 'python.exe'),  
        second_script_path
    ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
            print(f"Error while running the second script: {e}")
