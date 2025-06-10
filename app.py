from flask import Flask, request, render_template, redirect, url_for, session, flash
import os
import json
import pandas as pd
import cv2
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'sua-chave-secreta-super-dificil'

UPLOAD_FOLDER = "static/fotos"
USERS_FILE = "data/users.csv"
PROGRESS_FILE = "data/progresso_usuarios.json"
PONTOS_FILE = "data/pontos.csv"
STATUS_FILE = "status.json"  # Reintroduzido para comunicação com game.py


# --- Funções de Inicialização e Utilitários ---
def inicializar_arquivos():
    # (nenhuma mudança aqui, igual ao anterior)
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(USERS_FILE):
        pd.DataFrame(columns=["username", "password"]).to_csv(USERS_FILE, index=False)
    if not os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "w") as f:
            json.dump({}, f)
    if not os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "w") as f:
            json.dump({}, f)


# --- Funções de Validação de Imagem ---
# (nenhuma mudança aqui, a função comparar_com_orb continua igual)
def comparar_com_orb(nome_ponto, foto_path):
    pasta_referencia = f"data/referencia/{nome_ponto}"
    if not os.path.exists(pasta_referencia): return False
    imagens_ref = [os.path.join(pasta_referencia, f) for f in os.listdir(pasta_referencia) if
                   f.endswith((".jpg", ".png"))]
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


# --- Rotas de Autenticação (permanecem para o site) ---
@app.route("/login", methods=["GET", "POST"])
def login():
    # (nenhuma mudança aqui)
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        users_df = pd.read_csv(USERS_FILE)
        user_data = users_df[users_df['username'] == username]
        if not user_data.empty and check_password_hash(user_data.iloc[0]['password'], password):
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash("Usuário ou senha inválidos.")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    # (nenhuma mudança aqui)
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        users_df = pd.read_csv(USERS_FILE)
        if username in users_df['username'].values:
            flash("Este nome de usuário já existe.")
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password)
        new_user = pd.DataFrame([[username, hashed_password]], columns=["username", "password"])
        new_user.to_csv(USERS_FILE, mode='a', header=False, index=False)
        flash("Usuário registrado com sucesso! Faça o login.")
        return redirect(url_for('login'))
    return render_template("register.html")


@app.route("/logout")
def logout():
    # (nenhuma mudança aqui)
    session.pop('username', None)
    return redirect(url_for('login'))


# --- Rotas do Jogo ---

@app.route("/")
def home():
    # (nenhuma mudança aqui)
    if 'username' not in session:
        return redirect(url_for('login'))
    # ... (lógica do placar continua a mesma)
    pontos_df = pd.read_csv(PONTOS_FILE)
    with open(PROGRESS_FILE, 'r') as f:
        progresso = json.load(f)
    username = session['username']
    visitados_usuario = progresso.get(username, [])
    pontos_visitados_info = pontos_df[pontos_df['nome'].isin(visitados_usuario)]
    total = len(pontos_df)
    qtd_visitados = len(visitados_usuario)
    porcentagem = int((qtd_visitados / total) * 100) if total > 0 else 0
    return render_template("placar.html",
                           pontos=pontos_visitados_info.to_dict(orient="records"),
                           total=total, visitados=qtd_visitados,
                           porcentagem=porcentagem, username=username)


# ROTA MODIFICADA: Não precisa mais de login, recebe usuário pela URL
@app.route("/visitar/<nome_ponto>")
def visitar(nome_ponto):
    username = request.args.get("username", "visitante")
    return render_template("tirar_foto.html", nome=nome_ponto, username=username)


# ROTA MODIFICADA: Agora renderiza templates para sucesso e falha
@app.route("/upload", methods=["POST"])
def upload():
    nome_ponto = request.args.get("nome", "sem_nome")
    username = request.args.get("username", "visitante")
    file = request.files.get("arquivo")

    if file:
        # 1. Salva a foto
        caminho_foto = os.path.join(UPLOAD_FOLDER, f"{username}_{nome_ponto}.jpg")
        file.save(caminho_foto)

        # 2. Atualiza o status.json (para o game.py saber que a foto chegou)
        with open(STATUS_FILE, "r+") as f:
            status_temp = json.load(f)
            status_temp[nome_ponto] = caminho_foto
            f.seek(0)
            f.truncate()
            json.dump(status_temp, f)

        # 3. Valida a foto e atualiza o progresso permanente do usuário
        if comparar_com_orb(nome_ponto, caminho_foto):
            with open(PROGRESS_FILE, "r+") as f:
                progresso = json.load(f)
                if username not in progresso:
                    progresso[username] = []
                if nome_ponto not in progresso[username]:
                    progresso[username].append(nome_ponto)
                f.seek(0)
                f.truncate()
                json.dump(progresso, f)
            return render_template("sucesso_validacao.html", nome_ponto=nome_ponto, username=username)
        else:
            # Em vez de retornar um H1, renderiza a página de falha
            return render_template("falha_validacao.html", nome_ponto=nome_ponto)

    return "Nenhum arquivo enviado.", 400


# API para o Pygame (pode ser removida se o placar for apenas no site)
@app.route("/api/progresso/<username>")
def api_progresso(username):
    with open(PROGRESS_FILE, 'r') as f:
        progresso = json.load(f)
    visitados = progresso.get(username, [])
    return json.dumps(visitados)


if __name__ == '__main__':
    inicializar_arquivos()
    app.run(host='0.0.0.0', port=5000, debug=True)