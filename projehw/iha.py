

import socket                      # Ağ haberleşmesi için
import threading                   # Aynı anda telemetri + video çalıştırmak için
import time                        # Zaman damgası / bekleme
import json                        # Telemetriyi JSON formatına çevirmek için
import random                      # Sahte telemetri üretmek için
import cv2                         # OpenCV  kamera veya görüntü işleme için
import numpy as np                 # Kamera yoksa sentetik görüntü üretmek için

HOST = "127.0.0.1"                 # Yerel IP
TELEM_PORT = 9000                  # Telemetri TCP portu
VIDEO_PORT = 9001                  # Video TCP portu
TELEM_INTERVAL = 1.0               # Telemetri gönderme aralığı 
FPS = 5                            # Video kare hızı

stop_flag = threading.Event()      # Threadlere dur sinyali

def telemetry_packet():            # Telemetri paketi oluştur
    return {
        "x": round(random.uniform(-10,10),2),    # Rastgele x
        "y": round(random.uniform(-10,10),2),    # Rastgele y
        "alt": round(random.uniform(90,120),2),  # İrtifa
        "spd": round(random.uniform(0,15),2),    # Hız
        "bat": round(random.uniform(40,100),1),  # Pil %
        "ts": time.time()                        # Zaman damgası
    }

def serve_telem():                  # Telemetri sunucusu
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:  # TCP soketi
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # Port tekrarı
        s.bind((HOST, TELEM_PORT))                                # Bağlan
        s.listen(1)                                               
        print(f"[DRONE] Telemetry listening {HOST}:{TELEM_PORT}") 
        conn, addr = s.accept()                                   
        print(f"[DRONE] Telemetry client {addr}")                 
        with conn:
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1) # Gecikme azalt
            while not stop_flag.is_set():                         # Dur emri gelene kadar
                line = json.dumps(telemetry_packet()).encode() + b"\n" # JSON oluştur
                try:
                    conn.sendall(line)                            # Gönder
                except:
                    break                                         # Hata — çık
                time.sleep(TELEM_INTERVAL)                        # Bekle

def open_camera():                   
    try:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  
    except:
        cap = cv2.VideoCapture(0)                 
    if not cap.isOpened():
        try:
            cap = cv2.VideoCapture(0, cv2.CAP_MSMF) 
        except:
            pass
    return cap

def synthetic_frame(w=640, h=360, tick=0):        # Kamera yoksa sentetik kare
    img = np.zeros((h, w, 3), np.uint8)           
    x = (tick * 10) % (w + 100) - 50               
    cv2.rectangle(img,(max(0,x),h//2-20),(min(w,x+100),h//2+20),(0,255,0),-1)
    cv2.putText(img,time.strftime("Synthetic %H:%M:%S"),(10,30),
                cv2.FONT_HERSHEY_SIMPLEX,0.7,(255,255,255),2) # Saat yaz
    return img

def serve_video():                 # Video sunucusu
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # TCP soketi
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, VIDEO_PORT))                              # Port bağla
        s.listen(1)                                             
        print(f"[DRONE] Video listening {HOST}:{VIDEO_PORT}")   
        conn, addr = s.accept()                                 
        print(f"[DRONE] Video client {addr}")                   

        cap = open_camera()                                     # Kamera aç
        use_synth = not cap.isOpened()                          # Açılamıyorsa sentetik oluşturur
        tick = 0                                                

        with conn:
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            period = 1.0 / max(1, FPS)                          # Kare aralığı
            while not stop_flag.is_set():
                if use_synth:
                    frame = synthetic_frame(640,360,tick)       
                else:
                    ok, frame = cap.read()                      
                    if not ok:
                        use_synth = True
                        continue
                    frame = cv2.resize(frame,(640,360))         

                ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY),70])
                if not ok:
                    tick += 1
                    time.sleep(period)
                    continue

                data = buf.tobytes()                            
                size = len(data).to_bytes(4,"big")              

                try:
                    conn.sendall(size + data)                   
                except:
                    break

                tick += 1
                time.sleep(period)                              

        if cap.isOpened(): cap.release()                        

def main():                          # Program giriş
    t1 = threading.Thread(target=serve_telem, daemon=True) # Telemetri thread açtı
    t2 = threading.Thread(target=serve_video, daemon=True) # Video thread açtı
    t1.start(); t2.start()             # Başlat
    print("[DRONE] Started")           # Bilgi ver
    try:
        while t1.is_alive() and t2.is_alive():  
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop_flag.set()                
        print("[DRONE] Stopping...")   

if __name__ == "__main__":             
    main()                             


