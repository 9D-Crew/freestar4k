import subprocess as sp
import sys
print("This will install all packages required for using FreeStar")
ver = sys.version_info
supported = True
if ver.major < 3:
    print("Python 2 is not supported. Please upgrade to Python 3.")
    exit(1)
if ver.minor < 9:
    print("Python 3.8 and below are not supported. Expect errors!")
    supported = False
if ver.minor > 13:
    print("Python 3.14 and up are not supported. Expect errors!")
    supported = False

errors = 0
def download_package(name):
    global errors
    p = sp.Popen([sys.executable, "-m", "pip", "install", name, "--break-system-packages"], stdout=sp.PIPE)
    p.wait()
    if p.returncode != 0:
        print(f"Error installing package: {name}")
        errors += 1
    elif "satisfied" in p.stdout.read().decode():
        print(f"Package {pkg} is already installed")

for pkg in ["pygame-ce", "wxPython", "sounddevice", "requests", "ephem", "opencv-python", "av"]:
    print(f"Installing package {pkg}")
    download_package(pkg)

if errors:
    print("An error occurred during installation of packages.")
    if supported:
        print("Google probably has answers.")
    else:
        print("Try changing to a supported Python version.")
else:
    print("Done! You can now run launcher.py to start the launcher.")
