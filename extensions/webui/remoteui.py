"""
Light UI module for creating simple interfaces for applications.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from websockets.asyncio.server import serve
from threading import Thread
import asyncio
import json
import base64

sockets : set = set()
messages = asyncio.Queue()
loop = None

async def handler(websocket):
    sockets.add(websocket)
    print("added")
    try:
        await asyncio.Future()
    except Exception as e:
        print(e)
        sockets.remove(websocket)

async def broadcast():
    while True:
        msg = await messages.get()
        
        for ws in sockets:
            await ws.send(msg)

e = 0
def send_message(msg):
    if len(sockets) > 0:
        if loop is not None:
            loop.call_soon_threadsafe(messages.put_nowait, msg)
    
    #global e
    # if len(sockets) > 0:
    #     messages.put_nowait(msg)
    #     print(messages.qsize())
    # else:
    #     e += 1
    #     print("nc", e)

class RemoteHandler(BaseHTTPRequestHandler):
    routes = {}
    items = []
    dynamic_data = {}
    
    gridsize = (3, 6)
    
    port = 8000
    
    def do_GET(self):
        if self.path == "/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(list(self.dynamic_data.items())).encode())
            return
        html = """
        <!DOCTYPE html>
        <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Remote UI</title>
                <style>
                    button {{
                        border: 2px darkgray inset;
                        border-radius: 5px;
                        background-color: #DDDDDD;
                        width: 100%;
                        height: 100%;
                        font-size: max(5vw, 5vh);
                        color: black;
                    }}
                    progress {{
                        width: 100%;
                        height: 100%;
                    }}
                    button:hover {{
                        background-color: gray;
                    }}
                    .container {{
                        width: 100vw;
                        height: 100vh;
                    }}
                    body {{
                        margin: 0;
                        overflow: hidden;
                    }}
                    div {{
                        display: inline-block;
                        overflow: hidden;
                        text-align: center;
                    }}
                    h1 {{
                        margin: 0;
                        font-size: max(4vw, 4vh);
                        font-family: Arial, sans-serif;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    {body}
                </div>{dynamic}
            </body>
        </html>"""
        dynamic = """
                <script>
                    function handledata(data) {{
                        for (const element of data) {{
                            if (typeof element[1] == "number") {{
                                document.getElementById(element[0]).value = element[1];
                            }}
                            if (typeof element[1] == "string") {{
                                document.getElementById(element[0]).innerText = element[1];
                            }}
                        }}
                    }}
                    function getdata() {{
                        const r = fetch("/data").then(response => {{
                            if (!response.ok) {{
                                throw new Error("data error")
                            }}
                            return response.json();
                        }}).then(data => {{
                            handledata(data);
                        }}).catch(error => {{
                            console.error(error)
                        }});
                    }}
                    if ('WebSocket' in window) {{
                        const socket = new WebSocket(window.location.href.replace("{port}", "{port2}"));
                        socket.addEventListener("message", (event) => {{
                            handledata(JSON.parse(event.data));
                        }});
                    }} else {{
                        setInterval(getdata, 1000);
                    }}
                </script>
        """
        
        body = ""
        dynamic_used = False
        
        for item in self.items:
            if item[0] in ["dtext", "dbtn", "progress"]:
                dynamic_used = True
        
        for item in self.items:
            stylestr = f"width: {100/self.gridsize[0]*item[-2][0]}vw; height: {100/self.gridsize[1]*item[-2][1]}vh; position: absolute; left: {100/self.gridsize[0]*item[-1][0]}vw; top: {100/self.gridsize[1]*item[-1][1]}vh;"
            if item[0] == "btn":
                path = f"/btn/{item[2]}"
                body += f"<div style=\"{stylestr}\"><button onclick=\"fetch('{path}', {{method: 'POST'}})\">{item[1]}</button></div>"
            elif item[0] == "break":
                body += "<br>"
            elif item[0] == "text":
                body += f"<div style=\"{stylestr} display: grid; align-items: center;\"><h1>{item[1]}</h1></div>"
            elif item[0] == "dtext":
                body += f"<div style=\"{stylestr} display: grid; align-items: center;\"><h1 id={item[2]}>{item[1]}</h1></div>"
            elif item[0] == "dbtn":
                path = f"/btn/{item[2]}"
                body += f"<div style=\"{stylestr}\"><button onclick=\"fetch('{path}', {{method: 'POST'}})\" id={item[2]}>{item[1]}</button></div>"
            elif item[0] == "progress":
                body += f"<div style=\"{stylestr}\"><progress value=\"{item[1]}\" max=\"1\" id={item[2]}></progress></div>"
            elif item[0] == "img":
                stylestr = f"height: {100/self.gridsize[1]*item[-2][1]}vh; position: absolute; left: {100/self.gridsize[0]*item[-1][0]}vw; top: {100/self.gridsize[1]*item[-1][1]}vh; image-rendering: pixelated;"
                #no height str
                body += f"<img src=\"{item[1]}\" style=\"{stylestr}\">"
        
        self.send_response(200)
        self.end_headers()
        self.wfile.write(html.format(body=body, dynamic=dynamic.format(port=str(self.port), port2=str(self.port+1)) if dynamic_used else "").encode())

    def do_POST(self):
        length = int(self.headers['Content-Length'])
        body = self.rfile.read(length).decode()
        if self.path in RemoteHandler.routes:
            Thread(target=RemoteHandler.routes[self.path]).start()
        self.send_response(200)
        self.end_headers()

class Dynamic:
    def __init__(self, value, id):
        self.value = value
        self.id = id
    
    def modify(self, value):
        self.value = value
        RemoteHandler.dynamic_data[self.id] = self.value
        send_message(json.dumps([[self.id, value]]))

class RemoteUI:
    def __init__(self, port=8000, size=(3, 6)):
        self.port = port
        self.server = HTTPServer(('', port), RemoteHandler)
        self.gridsize = size
        RemoteHandler.gridsize = size
        RemoteHandler.port = port

    def add_button(self, label, id, callback, position=(1, 1), size=(1, 1)):
        path = f"/btn/{id}"
        RemoteHandler.routes[path] = callback
        RemoteHandler.items.append(["btn", label, id, callback, size, position])

    def add_text(self, label, position=(1, 1), size=(1, 1)):
        RemoteHandler.items.append(["text", label, size, position])
    
    def add_img(self, path, position=(1, 1), size=(1, 1)):
        with open(path, "rb") as f:
            img = f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
        RemoteHandler.items.append(["img", img, size, position])
    
    def add_dynamic_text(self, label, id, position=(1, 1), size=(1, 1)):
        RemoteHandler.items.append(["dtext", label, id, size, position])
        return Dynamic(label, id)

    def add_dynamic_button(self, label, id, callback, position=(1, 1), size=(1, 1)):
        path = f"/btn/{id}"
        RemoteHandler.routes[path] = callback
        RemoteHandler.items.append(["dbtn", label, id, callback, size, position])
        return Dynamic(label, id)
    
    def add_progressbar(self, value, id, position=(1, 1), size=(1, 1)):
        RemoteHandler.items.append(["progress", value, id, size, position])
        return Dynamic(value, id)

    async def _ws_main(self):
        async with serve(handler, "localhost", self.port+1):
            asyncio.create_task(broadcast())
            await asyncio.sleep(0)
            await asyncio.Future()

    def _start_ws(self):
        global loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        
        loop.run_until_complete(self._ws_main())
        
        return loop

    def start(self) -> Thread:
        th = Thread(target=self.server.serve_forever, daemon=True)
        th.start()
        th2 = Thread(target=self._start_ws, daemon=True)
        th2.start()
        return th, th2