"""Este script cria um aplicativo web Flask que permite ao usuário fazer upload de um vídeo MP4,
extrair o áudio, transcrever o áudio e baixar o áudio e a transcrição resultante."""

"""Antes da execução do programa, realizar a instação pip install Flask moviepy SpeechRecognition pydub werkzeug"""


import os
"""Importa o módulo OS, que fornece funções para interagir com o sistema operacional, como criar
diretórios e manipular caminhos de arquivos"""
from flask import Flask, request, redirect, url_for, send_from_directory, render_template
"""Importa componentes essenciais do Flask, um microframework (estruturas de aplicativos da web minimalistas) 
para web em Python. Estes componentes  são usados para criar a aplicação web, lidar com requisições, 
redirecionamentos, URLs, envio de arquivos e renderização de templates"""
from werkzeug.utils import secure_filename
"""Importa a função secure_filename da biblioteca Werkzeug, que é usada para garantir que o nome do arquivo 
enviado seja seguro e válido."""
import moviepy.editor as mp
"""Importa a biblioteca MoviePy e a renomeia como MP. Esta biblioteca é usada para manipulação de vídeo."""
import speech_recognition as sr
"""Importa a biblioteca SpeechRecognition, que é usada para reconhecimento de fala."""
from pydub import AudioSegment
"""Importa a classe AudioSegment da biblioteca Pydub, usada para manipulação de arquivos de áudio."""

# Configurações Flask
app = Flask(__name__) 
"""Cria uma instância da aplicação Flask"""
UPLOAD_FOLDER = 'uploads' 
"""Define o diretório onde os arquivos enviados serão armazenados."""
OUTPUT_FOLDER = 'output'  
"""Define o diretório onde os arquivos de saída (como o áudio extraído e a transcrição) serão armazenados."""
ALLOWED_EXTENSIONS = {'mp4'} 
"""Define as extensões de arquivo permitidas para upload."""

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
"""Configura os diretórios de upload e output na aplicação Flask."""

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
"""Função allowed verifica se um arquivo tem uma extensão permitida."""

def extract_audio_from_video(video_path, output_dir):
    """Função que extrai o áudio de um vídeo e salva como um arquivo WAV."""
    video = mp.VideoFileClip(video_path)
    audio_path = os.path.join(output_dir, "audio_extraido.wav")
    video.audio.write_audiofile(audio_path)
    return audio_path

def transcribe_audio(audio_path, output_dir, segment_length=60):
    """Função que divide o áudio em segmentos, transcreve cada segmento usando o 
    Google Speech Recognition e salva a transcrição em um arquivo de texto."""
    recognizer = sr.Recognizer()
    audio = AudioSegment.from_file(audio_path)
    duration = len(audio) // 1000
    segments = duration // segment_length + 1
    full_text = ""

    for i in range(segments):
        start_time = i * segment_length * 1000
        end_time = min((i + 1) * segment_length * 1000, len(audio))
        segment = audio[start_time:end_time]
        segment_path = os.path.join(output_dir, f"temp_segment_{i + 1}.wav")
        segment.export(segment_path, format="wav")

        with sr.AudioFile(segment_path) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data, language="pt-BR")
                print(f"Transcrição do segmento {i + 1}:")
                print(text)
                full_text += text + " "
            except sr.UnknownValueError:
                print(f"Google Speech Recognition não entendeu o áudio no segmento {i + 1}")
            except sr.RequestError as e:
                print(f"Erro na solicitação no segmento {i + 1}: {e}")

    transcription_path = os.path.join(output_dir, "transcricao.txt")
    with open(transcription_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    
    return transcription_path

@app.route('/', methods=['GET', 'POST']) 
def upload_file():
    """
    @app.route:
    Define a rota para a página principal que aceita métodos GET e POST.
    GET = Quando um usuário acessa a página inicial (/) pela primeira vez, é feita uma requisição GET 
    para o servidor. O servidor responde com o template HTML para upload de arquivos (upload.html).
    POST = Quando o usuário envia um arquivo através do formulário, é feita uma requisição POST para o servidor. 
    O servidor então processa o arquivo enviado, extrai o áudio, transcreve o áudio e retorna um template HTML 
    com links para download dos resultados (download.html).
    
    upload_file():
     Função que lida com o upload do arquivo, extração de áudio, transcrição e renderização das páginas HTML."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            audio_path = extract_audio_from_video(filepath, app.config['OUTPUT_FOLDER'])
            transcription_path = transcribe_audio(audio_path, app.config['OUTPUT_FOLDER'])
            return render_template('download.html', audio_file='audio_extraido.wav', transcription_file='transcricao.txt')
    return render_template('upload.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Define a rota para servir arquivos do diretório de uploads."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/output/<filename>')
def output_file(filename):
    """Define a rota para servir arquivos do diretório de output."""
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    """Bloco de código que garante que o servidor Flask será executado apenas se o script for 
    executado diretamente."""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    """Cria os diretórios de upload e output se eles não existirem."""
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    app.run(debug=True)
    """Inicia a aplicação Flask em modo debug."""
