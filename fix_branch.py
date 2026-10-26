import subprocess
print("Branch current state:")
print(subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True).stdout)
