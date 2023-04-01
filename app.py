from TTS.api import TTS
tts = TTS(model_name="tts_models/multilingual/multi-dataset/your_tts", progress_bar=False, gpu=True)
import whisper
model = whisper.load_model("small")
import torch
import torchaudio
from speechbrain.pretrained import SpectralMaskEnhancement
from scipy.io import wavfile
import noisereduce as nr
import gradio as gr
import openai

mes1 = [
    {"role": "system", "content": "You are a TOEFL examiner. Help me improve my oral Englsih and give me feedback."}
]

mes2 = [
    {"role": "system", "content": "You are a mental health therapist. Your name is Tina."}
]

mes3 = [
    {"role": "system", "content": "You are my personal assistant. Your name is Alice."}
]

res = []

def transcribe(apikey, upload, audio, choice1):

    openai.api_key = apikey
    
    # time.sleep(3)
    # load audio and pad/trim it to fit 30 seconds
    audio = whisper.load_audio(audio)
    audio = whisper.pad_or_trim(audio)

    # make log-Mel spectrogram and move to the same device as the model
    mel = whisper.log_mel_spectrogram(audio).to(model.device)

    # detect the spoken language
    _, probs = model.detect_language(mel)
    print(f"Detected language: {max(probs, key=probs.get)}")

    # decode the audio
    options = whisper.DecodingOptions()
    result = whisper.decode(model, mel, options)
    res.append(result.text)

    if choice1 == "TOEFL":
      messages = mes1
    elif choice1 == "Therapist":
      messages = mes2
    elif choice1 == "Alice":
      messages = mes3

    # chatgpt
    n = len(res)
    content = res[n-1]
    messages.append({"role": "user", "content": content})

    completion = openai.ChatCompletion.create(
      model = "gpt-3.5-turbo",
      messages = messages
    )

    chat_response = completion.choices[0].message.content

    messages.append({"role": "assistant", "content": chat_response})   

    tts.tts_to_file(chat_response, speaker_wav = upload, language="en", file_path="output.wav")
    
    rate, data = wavfile.read("output.wav")
    
    #reduced_noise = nr.reduce_noise(y=data, sr=rate, prop_decrease= 0.9, stationary=True)
    reduced_noise = nr.reduce_noise(y = data, sr=rate, prop_decrease= 0.9, thresh_n_mult_nonstationary=2, stationary=False)
    #reduced_noise = nr.reduce_noise(y = data, sr=rate, thresh_n_mult_nonstationary=2, stationary=False)

    wavfile.write("audio1.wav", rate, reduced_noise)

    enhance_model = SpectralMaskEnhancement.from_hparams(
    source="speechbrain/metricgan-plus-voicebank",
    savedir="pretrained_models/metricgan-plus-voicebank",
    run_opts={"device":"cuda"},
    )

    noisy = enhance_model.load_audio(
    "audio1.wav"
    ).unsqueeze(0)

    enhanced = enhance_model.enhance_batch(noisy, lengths=torch.tensor([1.]))
    torchaudio.save("enhanced.wav", enhanced.cpu(), 16000)

    return [result.text, chat_response, "enhanced.wav"]

output_1 = gr.Textbox(label="Speech to Text")
output_2 = gr.Textbox(label="ChatGPT Output")
output_3 = gr.Audio(label="Audio")

gr.Interface(
    title = '🥳💬💕 - TalktoAI，随时随地，谈天说地！', 
    theme="huggingface",
    description = "🤖 - 让有人文关怀的AI造福每一个人！AI向善，文明璀璨！TalktoAI，Enable the future！",
    fn=transcribe, 
    inputs=[
        gr.Textbox(lines=1, label = "请填写您的OpenAI_API_key"),
        gr.inputs.Audio(source="upload", label = "请上传您喜欢的声音", type="filepath"),
        gr.inputs.Audio(source="microphone", type="filepath"),
        gr.Radio(["TOEFL", "Therapist", "Alice"], label="TOEFL Examiner, Therapist Tina, or Assistant Alice?"),
    ],
    outputs=[
      output_1, output_2, output_3
    ],
    ).launch()
