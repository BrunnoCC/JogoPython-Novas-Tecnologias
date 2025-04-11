from flask import Flask, request, render_template
import os
import json
import pandas as pd

app = Flask(__name__)

UPLOAD_FOLDER = "static/fotos"
STATUS_FILE = "status.json"

# Criar a pasta de fotos se não existir
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Criar o status.json se não existir
if not os.path.exists(STATUS_FILE):
    with open(STATUS_FILE, "w") as f:
        json.dump({}, f)


@app.route("/")
def home():
    import pandas as pd
    df = pd.read_csv("data/pontos.csv")
    total = len(df)
    visitados = df[df['visitado'] == True]
    qtd_visitados = len(visitados)
    porcentagem = int((qtd_visitados / total) * 100)

    return render_template("placar.html",
                           pontos=visitados.to_dict(orient="records"),
                           total=total,
                           visitados=qtd_visitados,
                           porcentagem=porcentagem)


@app.route("/tirar_foto")
def tirar_foto():
    nome = request.args.get("nome", "sem_nome")
    return render_template("tirar_foto.html", nome=nome)


@app.route("/upload", methods=["POST"])
def upload():
    nome = request.args.get("nome", "sem_nome")
    file = request.files.get("arquivo")

    if file:
        caminho_foto = os.path.join(UPLOAD_FOLDER, f"{nome}.jpg")
        file.save(caminho_foto)
        print("Foto salva em:", caminho_foto)

        with open(STATUS_FILE, "r") as f:
            status = json.load(f)
        status[nome] = caminho_foto
        with open(STATUS_FILE, "w") as f:
            json.dump(status, f)

        return f"Foto enviada com sucesso para o ponto: {nome}"
    return "Nenhum arquivo enviado."


@app.route("/reset")
def reset_status():
    with open(STATUS_FILE, "w") as f:
        json.dump({}, f)
    return "Status reiniciado."


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
