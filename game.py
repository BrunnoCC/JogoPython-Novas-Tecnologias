import pygame
import pandas as pd
import os
import datetime
import cv2

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
player_size = 20
player_color = GREEN
player_speed = 5

# Carregar pontos turísticos
df = pd.read_csv("data/pontos.csv")

# Criar pasta para screenshots se não existir
if not os.path.exists("static/fotos"):
    os.makedirs("static/fotos")


# Função para desenhar tudo na tela
def draw_window():
    win.fill(WHITE)

    # Desenhar pontos turísticos
    for index, row in df.iterrows():
        color = RED if not row['visitado'] else (150, 150, 150)
        pygame.draw.circle(win, color, (int(row['x']), int(row['y'])), 10)

    # Desenhar jogador
    pygame.draw.rect(win, player_color, (player_pos[0], player_pos[1], player_size, player_size))

    pygame.display.update()


# Função para verificar se jogador está próximo de algum ponto e apertou espaço
def verificar_visita(tecla_foto):
    global df
    for index, row in df.iterrows():
        distancia = ((player_pos[0] - row['x']) ** 2 + (player_pos[1] - row['y']) ** 2) ** 0.5
        if distancia < 20 and not row['visitado']:
            font = pygame.font.SysFont(None, 24)
            msg = font.render(f"Pressione ESPAÇO para tirar foto de {row['nome']}", True, BLACK)
            win.blit(msg, (20, 20))
            pygame.display.update()

            if tecla_foto:
                print(f"Você visitou: {row['nome']}")
                filename = tirar_foto(row['nome'])
                if comparar_com_orb(row['nome'], filename):
                    df.at[index, 'visitado'] = True
                    df.to_csv("data/pontos.csv", index=False)
            break


# Função para tirar foto com a webcam
def tirar_foto(nome):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Erro ao acessar a câmera.")
        return None

    print("Tire a foto e pressione 's' para salvar.")
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        cv2.imshow("Pressione 's' para salvar a foto", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            filename = f"static/fotos/{nome}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            cv2.imwrite(filename, frame)
            print(f"Foto salva: {filename}")
            break

    cap.release()
    cv2.destroyAllWindows()
    return filename


# Comparação com ORB (estrutura visual)
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

            if similaridade < 50:  # quanto menor, melhor
                melhor_match += 1

    if melhor_match > 0:
        print("Foto validada com sucesso! ✅")
        return True
    else:
        print("Foto não corresponde ao ponto turístico. ❌")
        return False


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
