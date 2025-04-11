import pygame
import pandas as pd
import os
import datetime
import cv2
import urllib.parse
import urllib.request
import io
import json
import time
import sys
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
GREEN = (0, 255, 0)

# Jogador
player_pos = [50, 50]
player_size = 15
player_color = BLACK
player_speed = 5

# Configurações da tela
largura, altura = 800, 600
tela = pygame.display.set_mode((largura, altura))
pygame.display.set_caption("Turista GO - Brasília Edition")

# Carregar o mapa
mapa = pygame.image.load("mapa.png")
mapa = pygame.transform.scale(mapa, (largura, altura))  # ajusta ao tamanho da tela
# Carregar pontos turísticos
df = pd.read_csv("data/pontos.csv")

# Criar pastas se não existirem
if not os.path.exists("static/fotos"):
    os.makedirs("static/fotos")

if not os.path.exists("status.json"):
    with open("status.json", "w") as f:
        json.dump({}, f)


# Função para desenhar tudo na tela
def draw_window():
    tela.blit(mapa, (0, 0))  # desenha o mapa antes de qualquer coisa

    # Desenhar pontos turísticos
    for index, row in df.iterrows():
        color = RED if not row['visitado'] else (150, 150, 150)
        pygame.draw.circle(tela, color, (int(row['x']), int(row['y'])), 10)

    # Desenhar jogador
    pygame.draw.rect(tela, player_color, (player_pos[0], player_pos[1], player_size, player_size))

    pygame.display.update()


# Gera o QR Code como imagem com api.qrserver.com
def gerar_qrcode_surface_google(url):
    url_encoded = urllib.parse.quote_plus(url)
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={url_encoded}"
    response = urllib.request.urlopen(qr_url)
    image_bytes = response.read()
    image_file = io.BytesIO(image_bytes)
    qr_surface = pygame.image.load(image_file)
    return qr_surface


def get_ipv4():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Faz uma conexão fake para descobrir o IP real da máquina
        s.connect(('8.8.8.8', 80))  # 8.8.8.8 é o DNS do Google
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip



# Espera o status.json ser atualizado com a confirmação
def esperar_validacao(nome):
    ip = get_ipv4()

    url = f"http://{ip}:5000/tirar_foto?nome={urllib.parse.quote(nome)}"
    qr_surface = gerar_qrcode_surface_google(url)

    # Limpa o valor antigo do status antes de começar
    with open("status.json", "r") as f:
        status = json.load(f)

    status[nome] = ""  # Limpa a chave atual
    with open("status.json", "w") as f:
        json.dump(status, f)

    print(f"Você está perto de: {nome}")
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
        msg = font.render("Escaneie o QR Code para enviar a foto", True, BLACK)
        win.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 + 170))
        pygame.display.update()

        # Checar se o status.json foi atualizado
        with open("status.json", "r") as f:
            status = json.load(f)

        if nome in status and status[nome] != "":
            waiting = False
            return comparar_com_orb(nome, status[nome])

        # Se passar muito tempo, sai
        if time.time() - tempo_inicial > 120:
            print("Tempo esgotado para enviar a foto.")
            return False


# Comparação com ORB
def comparar_com_orb(nome, foto_path):
    pasta = f"data/referencia/{nome}"
    if not os.path.exists(pasta):
        print(f"Nenhuma imagem de referência encontrada para {nome}.")
        return False

    imagens_ref = [os.path.join(pasta, f) for f in os.listdir(pasta) if f.endswith((".jpg", ".png"))]
    if not imagens_ref:
        print(f"Nenhuma imagem de referência válida encontrada em {pasta}.")
        return False

    img_capturada = cv2.imread(foto_path, cv2.IMREAD_GRAYSCALE)
    if img_capturada is None:
        print("Erro ao carregar a imagem capturada.")
        return False

    orb = cv2.ORB_create()
    kp1, des1 = orb.detectAndCompute(img_capturada, None)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    melhor_match = 0
    for ref_path in imagens_ref:
        img_ref = cv2.imread(ref_path, cv2.IMREAD_GRAYSCALE)
        if img_ref is None:
            continue

        kp2, des2 = orb.detectAndCompute(img_ref, None)
        if des2 is None or des1 is None:
            continue

        matches = bf.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)

        if len(matches) > 0:
            similaridade = sum([m.distance for m in matches[:20]]) / len(matches[:20])
            print(f"Similaridade com {ref_path}: {similaridade:.2f}")
            if similaridade < 50:
                melhor_match += 1

    if melhor_match > 0:
        print("Foto validada com sucesso! ✅")
        return True
    else:
        print("Foto não corresponde ao ponto turístico. ❌")
        return False


# Verifica se o jogador está próximo de algum ponto
def verificar_visita(tecla_foto):
    global df
    for index, row in df.iterrows():
        distancia = ((player_pos[0] - row['x']) ** 2 + (player_pos[1] - row['y']) ** 2) ** 0.5
        if distancia < 20 and not row['visitado']:
            font = pygame.font.SysFont(None, 24)
            msg = font.render(f"Pressione ESPAÇO para visitar {row['nome']}", True, BLACK)
            win.blit(msg, (20, 20))
            pygame.display.update()

            if tecla_foto:
                if esperar_validacao(row['nome']):
                    df.at[index, 'visitado'] = True
                    df.to_csv("data/pontos.csv", index=False)
            break


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
    if keys[pygame.K_LEFT]:
        player_pos[0] -= player_speed
    if keys[pygame.K_RIGHT]:
        player_pos[0] += player_speed
    if keys[pygame.K_UP]:
        player_pos[1] -= player_speed
    if keys[pygame.K_DOWN]:
        player_pos[1] += player_speed

    draw_window()
    verificar_visita(tecla_foto)

pygame.quit()
