import socket                      # ağ soketi
import threading                   # telemetri + video eşzamanlı almak için
import json                        # gelen telemetriyi parse etmek için
import cv2                         # video görüntüleme
import numpy as np                 # buffer işlemleri için
import time                        # bekleme amaçlı

HOST = "127.0.0.1"                 # bağlanılacak IHA IP set
TELEM_PORT = 9000                  # telemetri TCP port set
VIDEO_PORT = 9001                  # video TCP port set

stop_flag = threading.Event()      # thread durdurma sinyali

def recv_telemetry():              # telemetri alma thread fonksiyonu
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:   # TCP soketi oluştur
        s.settimeout(5)              # bağlantı zaman aşımı saniye set
        print("[GCS] Telemetry connect")  
        s.connect((HOST, TELEM_PORT)) # IHA telem portuna bağlan
        buffer = b""                 
        while not stop_flag.is_set():# durdurma sinyali gelene kadar
            try:
                chunk = s.recv(4096) # soketten veri al
                if not chunk:        
                    print("[GCS] Telemetry closed")
                    break
                buffer += chunk      # buffer'a ekle
                while b"\n" in buffer:         
                    line, buffer = buffer.split(b"\n", 1) 
                    try:
                        data = json.loads(line.decode("utf-8")) 
                        print("[GCS] TELEMETRY:", data)         
                    except:
                        pass
            except socket.timeout:
                continue
            except Exception as e:   
                print("[GCS] telem err:", e)
                break

def recv_video():                   # video alma thread fonksiyonu
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:   # TCP soketi
        s.settimeout(5)              
        print("[GCS] Video connect")
        s.connect((HOST, VIDEO_PORT)) # IHA video portuna bağlan
        while not stop_flag.is_set():
            try:
                hdr = s.recv(4)      
                if len(hdr) < 4:     
                    print("[GCS] video closed")
                    break
                size = int.from_bytes(hdr, "big")  
                buf = b""                       
                while len(buf) < size:          
                    part = s.recv(size - len(buf))  
                    if not part: break
                    buf += part
                frame = cv2.imdecode(np.frombuffer(buf, np.uint8), cv2.IMREAD_COLOR)  
                

                if frame is not None:           
                    cv2.imshow("VIDEO", frame)  
                    if cv2.waitKey(1) == 27:    
                        stop_flag.set()
                        break
            except Exception as e:
                print("[GCS] video err:", e)
                break
        cv2.destroyAllWindows()                 # pencereyi kapat

def main():                     
    t1 = threading.Thread(target=recv_telemetry, daemon=True) # telem thread
    t2 = threading.Thread(target=recv_video, daemon=True)     # video thread
    t1.start(); t2.start()            # threadleri başlat
    print("[GCS] Started") 
    try:
        while t1.is_alive() and t2.is_alive(): # programı canlı tut
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop_flag.set()              # durdur
        print("[GCS] Stopping...")   

if __name__ == "__main__":
    main()


