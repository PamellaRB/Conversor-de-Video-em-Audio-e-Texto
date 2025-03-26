from flask import Flask, request, redirect, url_for, send_from_directory, render_template, jsonify
# Importa as bibliotecas necessárias do Flask para criar o servidor e manipular requisições.

import os
import threading
# Importa bibliotecas para manipulação de arquivos e para criar threads para o processamento em segundo plano.

from werkzeug.utils import secure_filename
# Importa uma função que garante que o nome do arquivo seja seguro para salvar.

from moviepy import VideoFileClip
# Importa o MoviePy para manipulação de vídeos (no caso, extrair áudio de vídeos).

import speech_recognition as sr
# Importa o SpeechRecognition para transcrição de áudio.

from pydub import AudioSegment
# Importa o PyDub para manipulação de arquivos de áudio.

app = Flask(__name__)
# Cria a instância principal do aplicativo Flask.

app.secret_key = 'segredo'  # Necessário para usar 'session'
# Define uma chave secreta necessária para o uso de sessões no Flask.

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'mp4'}
# Define o diretório de uploads, o diretório de saída e as extensões permitidas para arquivos.

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
# Configura os diretórios de upload e saída para o Flask.

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
# Cria os diretórios de upload e saída, caso não existam.

# Variável global para status do processamento
processing_status = {'completed': False}
# Cria uma variável global para controlar o status do processamento do vídeo (se foi concluído ou não).

def allowed_file(filename):
    # Função que verifica se o arquivo enviado possui a extensão permitida.
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_audio_from_video(video_path, output_dir):
    """Extrai o áudio do vídeo e salva como WAV"""
    # Função para extrair o áudio de um vídeo.
    video = VideoFileClip(video_path)
    audio_path = os.path.join(output_dir, "audio_extraido.wav")
    video.audio.write_audiofile(audio_path)
    return audio_path

def transcribe_audio(audio_path, output_dir):
    """Transcreve o áudio usando Google Speech Recognition"""
    # Função para transcrever o áudio usando a API de reconhecimento de fala do Google.
    recognizer = sr.Recognizer()
    audio = AudioSegment.from_file(audio_path)
    duration = len(audio) // 1000  # Converte a duração do áudio para segundos.
    segments = duration // 60 + 1  # Divide o áudio em segmentos de 1 minuto.
    full_text = ""  # Variável para armazenar o texto transcrito.

    for i in range(segments):
        start_time = i * 60 * 1000  # Início do segmento (em milissegundos).
        end_time = min((i + 1) * 60 * 1000, len(audio))  # Fim do segmento.
        segment = audio[start_time:end_time]  # Extrai o segmento de áudio.
        segment_path = os.path.join(output_dir, f"temp_segment_{i + 1}.wav")
        segment.export(segment_path, format="wav")  # Salva o segmento como um arquivo WAV.

        with sr.AudioFile(segment_path) as source:
            audio_data = recognizer.record(source)  # Converte o áudio em dados utilizáveis.
            try:
                text = recognizer.recognize_google(audio_data, language="pt-BR")  # Reconhece o áudio e converte para texto.
                full_text += text + " "
            except sr.UnknownValueError:
                pass  # Caso não consiga reconhecer, ignora o erro.
            except sr.RequestError as e:
                print(f"Erro no reconhecimento: {e}")

    transcription_path = os.path.join(output_dir, "transcricao.txt")
    with open(transcription_path, "w", encoding="utf-8") as f:
        f.write(full_text)  # Salva a transcrição em um arquivo de texto.

    return transcription_path

def process_video(filename):
    """Função para processar vídeo em uma thread separada"""
    # Função que processa o vídeo, extraindo o áudio e fazendo a transcrição.
    global processing_status
    processing_status['completed'] = False  # Reseta o status de processamento.

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    audio_path = extract_audio_from_video(filepath, app.config['OUTPUT_FOLDER'])
    transcribe_audio(audio_path, app.config['OUTPUT_FOLDER'])
    
    # Atualiza o status quando o processamento for concluído.
    processing_status['completed'] = True

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    """Página inicial para upload"""
    # Função que renderiza a página de upload de arquivos.
    global processing_status
    if request.method == 'POST':
        file = request.files['file']  # Pega o arquivo enviado via POST.
        if file and allowed_file(file.filename):  # Verifica se o arquivo tem a extensão permitida.
            filename = secure_filename(file.filename)  # Torna o nome do arquivo seguro.
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)  # Salva o arquivo no diretório de upload.

            # Inicia o processamento em segundo plano.
            thread = threading.Thread(target=process_video, args=(filename,))
            thread.start()

            return redirect(url_for('loading_page'))  # Redireciona para a página de carregamento.
    return render_template('upload.html')  # Renderiza o template da página de upload.

@app.route('/loading')
def loading_page():
    """Tela de carregamento"""
    return render_template('loading.html')  # Renderiza a página de carregamento enquanto processa.

@app.route('/check_status')
def check_status():
    """Verifica se o processamento foi concluído"""
    return jsonify({'processing_complete': processing_status['completed']})  # Retorna o status do processamento em formato JSON.

@app.route('/download')
def download_page():
    """Tela de download"""
    return render_template('download.html', audio_file="audio_extraido.wav", transcription_file="transcricao.txt")  
    # Renderiza a página de download com os arquivos gerados (áudio extraído e transcrição).

@app.route('/output/<filename>')
def output_file(filename):
    """Serve arquivos do diretório output"""
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)  
    # Serve arquivos do diretório de saída para download.

if __name__ == '__main__':
    app.run(debug=True)
    # Inicia o aplicativo Flask em modo de depuração.
