import pygame
import pandas as pd
import os
import cv2
import urllib.parse
import urllib.request
import io
import json
import time
import socket

# Inicializar Pygame
pygame.init()

# Configurações da janela
WIDTH, HEIGHT = 800, 600
win = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Turista GO - Brasília Edition")

# Cores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GRAY = (150, 150, 150)

# Jogador
player_pos = [50, 50]
player_size = 15
player_color = BLACK
player_speed = 5

# Carregar o mapa e pontos
mapa = pygame.image.load("mapa.png")
mapa = pygame.transform.scale(mapa, (WIDTH, HEIGHT))
df = pd.read_csv("data/pontos.csv")
# Garante que a coluna 'visitado' seja booleana
df['visitado'] = df['visitado'].astype(bool)

# --- PERGUNTA O USUÁRIO NO INÍCIO ---
PLAYER_USERNAME = input("Digite seu nome de usuário para começar: ")


# Função para desenhar tudo na tela
def draw_window():
    win.blit(mapa, (0, 0))
    for index, row in df.iterrows():
        color = GRAY if row['visitado'] else RED
        pygame.draw.circle(win, color, (int(row['x']), int(row['y'])), 10)
    pygame.draw.rect(win, player_color, (player_pos[0], player_pos[1], player_size, player_size))
    pygame.display.update()


# --- FUNÇÕES RESTAURADAS DO ORIGINAL ---

def get_ipv4():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def gerar_qrcode_surface_google(url):
    url_encoded = urllib.parse.quote_plus(url)
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={url_encoded}"
    response = urllib.request.urlopen(qr_url)
    image_file = io.BytesIO(response.read())
    qr_surface = pygame.image.load(image_file)
    return qr_surface


def comparar_com_orb(nome, foto_path):
    # Esta função pode ser mantida aqui para dar feedback visual imediato no jogo
    # ou pode ser removida se a validação for confiada apenas ao servidor.
    # Por enquanto, vamos manter para feedback.
    pasta = f"data/referencia/{nome}"
    if not os.path.exists(pasta): return False
    imagens_ref = [os.path.join(pasta, f) for f in os.listdir(pasta) if f.endswith((".jpg", ".png"))]
    if not imagens_ref: return False
    img_capturada = cv2.imread(foto_path, cv2.IMREAD_GRAYSCALE)
    if img_capturada is None: return False
    orb = cv2.ORB_create()
    kp1, des1 = orb.detectAndCompute(img_capturada, None)
    if des1 is None: return False
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    melhor_match = 0
    for ref_path in imagens_ref:
        img_ref = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
        if img_ref is None: continue
        kp2, des2 = orb.detectAndCompute(img_ref, None)
        if des2 is None: continue
        matches = bf.match(des1, des2)
        if len(matches) > 20:
            similaridade = sum(m.distance for m in matches[:20]) / 20
            if similaridade < 50:
                melhor_match += 1
    return melhor_match > 0


def esperar_validacao(nome_ponto):
    ip = get_ipv4()
    # A URL agora inclui o nome do ponto E o username
    url = f"http://{ip}:5000/visitar/{urllib.parse.quote(nome_ponto)}?username={urllib.parse.quote(PLAYER_USERNAME)}"
    qr_surface = gerar_qrcode_surface_google(url)

    # Limpa o status antigo do ponto atual
    with open("status.json", "r") as f:
        status = json.load(f)
    if nome_ponto in status:
        status[nome_ponto] = ""
    with open("status.json", "w") as f:
        json.dump(status, f)

    print(f"Você está perto de: {nome_ponto}")
    print("Abra a câmera do celular e escaneie o QR Code para tirar a foto!")

    waiting = True
    tempo_inicial = time.time()
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return False

        win.fill(WHITE)
        win.blit(qr_surface, (WIDTH // 2 - 150, HEIGHT // 2 - 150))
        font = pygame.font.SysFont(None, 28)
        msg = font.render(f"Escaneie o QR Code (jogador: {PLAYER_USERNAME})", True, BLACK)
        win.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 + 170))
        pygame.display.update()

        # Checar se o status.json foi atualizado
        with open("status.json", "r") as f:
            status = json.load(f)

        if nome_ponto in status and status[nome_ponto] != "":
            waiting = False
            # O servidor já fez a validação, mas podemos dar um feedback aqui também
            print("Foto recebida pelo servidor. Verificando...")
            if comparar_com_orb(nome_ponto, status[nome_ponto]):
                print("Foto validada com sucesso! ✅")
                return True
            else:
                print("Foto não corresponde ao ponto turístico. ❌")
                return False

        if time.time() - tempo_inicial > 120:
            print("Tempo esgotado.")
            return False


def verificar_visita(tecla_foto):
    global df
    for index, row in df.iterrows():
        distancia = ((player_pos[0] - row['x']) ** 2 + (player_pos[1] - row['y']) ** 2) ** 0.5
        if distancia < 20 and not row['visitado']:
            font = pygame.font.SysFont(None, 24)
            msg = font.render(f"Pressione ESPAÇO para visitar {row['nome']}", True, BLACK, WHITE)
            win.blit(msg, (20, 20))

            if tecla_foto:
                if esperar_validacao(row['nome']):
                    df.at[index, 'visitado'] = True
                    # Não precisamos mais salvar o CSV, o progresso é local da sessão de jogo.
                    # O progresso real está no servidor.
            break  # sai do loop depois de encontrar o primeiro ponto


# Loop principal
run = True
clock = pygame.time.Clock()
while run:
    clock.tick(30)
    tecla_foto = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            tecla_foto = True

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]: player_pos[0] -= player_speed
    if keys[pygame.K_RIGHT]: player_pos[0] += player_speed
    if keys[pygame.K_UP]: player_pos[1] -= player_speed
    if keys[pygame.K_DOWN]: player_pos[1] += player_speed

    draw_window()
    verificar_visita(tecla_foto)
    pygame.display.update()  # Adicionado para garantir que a msg de pressionar espaço apareça

pygame.quit()