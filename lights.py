import socket
import tkinter as tk
import threading as th

leds = [False for _ in range(13)]

root = tk.Tk()
root.title("FreeLights")

leds2 = [
    "Satellite Video",
    "Satellite Data",
    "Local Video",
    "Not Assigned",
    "Commercial Pre-Roll",
    "Commercial On-Air",
    "Modem in-use",
    "Not Assigned",
    "Not Assigned",
    "System Error",
    "Ring Indicator",
    "Carrier Detect",
    "Charging Indicator"
]

colors = [
    "G", "G", "G", "G", "A", "A", "A", "R", "R", "R", "G", "G", "R"
]

leds3 = []
for i in range(13):
    tk.Frame(root, height=5).pack()
    fr = tk.Frame(root, bg={"R": "dark red", "A": "DarkOrange4", "G": "dark green"}[colors[i]], height=20)
    leds3.append(fr)
    fr.pack(fill=tk.X, expand=True)
    tk.Label(root, text=leds2[i]).pack()
    tk.Frame(root, height=5).pack()

def updateleds():
    global leds, leds3
    for i, frame in enumerate(leds3):
        frame.configure(bg=[{"R": "dark red", "A": "DarkOrange4", "G": "dark green"}, {"R": "red", "A": "DarkOrange1", "G": "lime green"}][leds[i]][colors[i]])

def updater():
    global leds
    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 4000))
        sock.sendall("status".encode())
        e = sock.recv(1024).decode()
        leds4 = []
        for l in e.split("\n"):
            if l.startswith("leds"):
                for l2 in l.split(" ")[1]:
                    leds4.append(bool(int(l2)))
        leds = leds4
        updateleds()
        while True:
            e = sock.recv(1024).decode()
            if e.startswith("led"):
                e2 = e.split(" ")
                leds[int(e2[1])] = bool(int(e2[2]))
                updateleds()

th.Thread(target=updater).start()

root.mainloop()