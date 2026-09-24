from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello_world():
    return '<h1>Halo! Flask berhasil dijalankan di komputer saya.</h1>'

if __name__ == '__main__':
    app.run(debug=True)
