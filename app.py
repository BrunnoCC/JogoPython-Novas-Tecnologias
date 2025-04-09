from flask import Flask, jsonify, render_template
import pandas as pd

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("placar.html")

@app.route("/api/placar")
def placar():
    df = pd.read_csv("data/pontos.csv")
    total = len(df)
    visitados = df["visitado"].sum()
    return jsonify({
        "total_pontos": total,
        "visitados": int(visitados),
        "porcentagem": round((visitados / total) * 100, 2)
    })

@app.route("/api/visitados")
def visitados():
    df = pd.read_csv("data/pontos.csv")
    visitados_df = df[df["visitado"] == True]
    return visitados_df.to_json(orient="records")

if __name__ == "__main__":
    app.run(debug=True)
