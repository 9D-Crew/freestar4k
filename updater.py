import requests as r
import os
print("FreeStar Updater v1.0.0")
try:
    tags = r.get("https://api.github.com/repos/9D-Crew/freestar4k/tags").json()
except:
    print("A network error has occured.")
    exit(1)
try:
    commits = r.get("https://api.github.com/repos/9D-Crew/freestar4k/commits").json()
except:
    print("A network error has occured.")
    exit(1)
def yn(prompt, default_true):
    while True:
        response = input(f"{prompt} [{'Y/n' if default_true else 'y/N'}]: ").strip().rstrip()
        if default_true:
            if not response:
                return True
            if response.lower() == "n":
                return False
            else:
                print("Invalid input. Please choose Y or N.")
        else:
            if not response:
                return False
            if response.lower() == "y":
                return True
            else:
                print("Invalid input. Please choose Y or N.")
def detect():
    if os.path.exists("main.py"):
        with open("main.py", "r") as f:
            try:
                content = f.read()
                ix = content.index("set_caption")
                content = content[ix:]
                ix = content.index("v")
                content = content[ix:]
                ix = content.index("\"")
                content = content[:ix]
                content = content.strip()
                return content
            except:
                return
if not os.path.exists("commit.txt"):
    print("This is your first time running the updater!")
    print("Attempting to detect release...")
    detection = detect()
    if detection:
        print(f"Detected release {detection} minimum")
        commit = detection
    else:
        print(f"No detected version! Assuming latest release.")
        commit = tags[0]['name']
    with open("commit.txt", "w") as f:
        f.write(commit)
else:
    with open("commit.txt", "r") as f:
        commit = f.read().strip()
print("WARNING: Any modifications made to FreeStar's files will be removed upon updating!")
print("Which version would you like to download?")
print(f"A. Release ({tags[0]['name']})" + (" (Already Installed)" if commit == tags[0]['name'] else ""))
print(f"B. Unstable (commit {commits[0]['sha'][:8]})" + (" (Already Installed)" if commit == commits[0]['sha'] else (" (Currently Same as Stable)" if commit == tags[0]['commit']['sha'][:8] else "")))
print(f"X. Exit the program")
def get_changed(from_c, to_c):
    comp = r.get(f"https://api.github.com/repos/9D-Crew/freestar4k/compare/{from_c}...{to_c}").json()
    changed = []
    for f in comp.get("files", []):
        changed.append({"filename": f["filename"], "status": f["status"], "url": f.get("raw_url")})
    return changed

def download(url, dst):
    dr = os.path.dirname(dst)
    if dr:
        os.makedirs(dr, exist_ok=True)
    rq = r.get(url)
    rq.raise_for_status()
    with open(dst, "wb") as f:
        f.write(rq.content)

def update(to_c):
    if commit == to_c:
        print("Already up-to-date.")
        return
    changes = get_changed(commit, to_c)
    print(f"Updating {len(changes)} files...")

    for change in changes:
        status = change["status"]
        filename = change["filename"]

        if status in ("modified", "added"):
            print(f"Downloading {filename}")
            download(change["url"], filename)

        elif status == "removed":
            print(f"Removing {filename}")
            if os.path.exists(filename):
                os.remove(filename)
    with open("commit.txt", "w") as f:
        f.write(to_c)
    
while True:
    ans = input("Answer (A/B/X): ").lower()
    if ans == "a":
        print(f"Updating to {tags[0]['name']}...")
        update(tags[0]['name'])
        break
    elif ans == "b":
        print(f"Updating to {commits[0]['sha'][:8]}...")
        update(commits[0]['sha'])
        break
    elif ans == "x":
        break
    else:
        print("Invalid answer. Please select A/B/X.")