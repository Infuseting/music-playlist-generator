import argparse
import essentia.standard as es
import numpy as np
import os
import yt_dlp
from db import DB
from music import Music
import json as JSON
class Import:
    def __init__(self, ytb_links, output_path):
        self.ytb_links = ytb_links
        self.output_path = output_path
        self.db = DB(output_path)
        self.opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320', 
            }],
            'outtmpl': f'{os.path.join(self.output_path, "%(title)s.%(ext)s")}',
            'quiet': False, 
        }
    def download_audio(self, link):
        with yt_dlp.YoutubeDL(self.opts) as ydl:
            try:
                ydl.download([link])
            except Exception as e:
                print(f"An error occurred while downloading: {e}")
                return None
    def get_informations(self, link):
        with yt_dlp.YoutubeDL(self.opts) as ydl:
            try:
                info = ydl.extract_info(link, download=False)
                
                return info
            except Exception as e:
                print(f"An error occurred while extracting information: {e}")
                return None
    def import_music(self):
        for link in self.ytb_links:
            self.download_audio(link)
            info =self.get_informations(link)
            analyse = self.analyse(os.path.join(self.output_path, f"{info['title']}.mp3"))
            print(f"Importing music from YouTube link: {link}")
            music = Music(os.path.join(self.output_path, f"{info['title']}.mp3"))
            music.insert_metadata(
                genre=[analyse['genre']],
                authors=info.get('creators', None) ,
                mood=analyse['happy_mood_probability'] / 100.0, 
                energy=analyse['energy'],
                bpm=analyse['bpm'], 
                danceability=analyse['danceability'], 
                popularity=max(min(info['view_count'] / 1e9 , 0.0), 1.0) , 
                instrumental=analyse['vocal_probability'] > 0.3, 
                year=info.get('upload_date', "19000101")[:4],
                copyright=False
            )
            self.db.insert_music(music)
    def analyse(self, path):

        print(f"🎵 Analyse de {path} en cours...\n")
        audio_44k = es.MonoLoader(filename=path, sampleRate=44100)()
        audio_16k = es.MonoLoader(filename=path, sampleRate=16000)()
        print("⏳ Calcul du rythme et de l'énergie...")
        bpm, _, _, _, _ = es.RhythmExtractor2013(method="multifeature")(audio_44k)
        energy = es.Energy()(audio_44k)
        danceability, _ = es.Danceability()(audio_44k)

        print(f"  👉 BPM : {bpm:.0f}")
        print(f"  👉 Énergie globale : {energy:.4f}")
        print(f"  👉 Danceability : {danceability:.4f} (plus c'est haut, plus c'est dansant)\n")

        # 3. ANALYSE IA (Instrumental & Mood)
        # 3. ANALYSE IA (Instrumental & Mood)
        print("🧠 Analyse de l'audio par l'Intelligence Artificielle...")

        # --- Détection Instrumental vs Voix ---
        # TensorflowPredictMusiCNN gère le découpage et le spectrogramme automatiquement
        model_inst = es.TensorflowPredictMusiCNN(graphFilename="models/voice_instrumental-musicnn-msd-2.pb")
        predictions_inst = model_inst(audio_16k)

        # On fait la moyenne des prédictions (l'IA sort une prédiction par patch de 3 secondes)
        moyenne_inst = np.mean(predictions_inst, axis=0) 
        print(f"  👉 Probabilité Instrumental : {moyenne_inst[0]:.1%}")
        print(f"  👉 Probabilité Présence de Voix : {moyenne_inst[1]:.1%}")

        # --- Détection du Mood (Joie / Valence) ---
        model_happy = es.TensorflowPredictMusiCNN(graphFilename="models/mood_happy-musicnn-msd-2.pb")
        predictions_happy = model_happy(audio_16k)

        
        moyenne_happy = np.mean(predictions_happy, axis=0)
        print(f"  👉 Probabilité Mood Joyeux : {moyenne_happy[1]:.1%}")
                
        model_genre = es.TensorflowPredictMusiCNN(graphFilename="models/genre_rosamerica-musicnn-msd-2.pb")
        predictions_genre = model_genre(audio_16k)
        moyenne_genre = np.mean(predictions_genre, axis=0)
        liste_genres = ['Classique',  'Hip Hop', 'Jazz', 'Pop', 'R&B', 'Rock', 'Voix parlée']
        index_dominant = np.argmax(moyenne_genre)
        genre_dominant = liste_genres[index_dominant]
        print(f"  👉 Genre principal détecté : {genre_dominant} (avec {moyenne_genre[index_dominant]:.1%} de certitude)")
        return {
            "bpm": bpm,
            "energy": max(min(energy / 1e7, 0.0),1.0),
            "danceability": max(min(danceability, 0.0),1.0),
            "instrumental_probability": moyenne_inst[0],
            "vocal_probability": moyenne_inst[1],
            "happy_mood_probability": moyenne_happy[1],
            "genre": genre_dominant
        }
def max(a, b):
    return a if a > b else b
def min(a, b):
    return a if a < b else b
            
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Music Metadata Inserter")
    parser.add_argument("--ytb_link", type=str, nargs='+', required=True, help="YouTube link(s) of the music to insert metadata into")
    parser.add_argument("--output", type=str, default="audio_files/", help="Path to save the music file with inserted metadata")
    args = parser.parse_args()
    Import(args.ytb_link, args.output).import_music()