import argparse
import os
import yt_dlp
from db import DB
from music import Music
import json as JSON
from logging_config import get_logger

try:
    import essentia.standard as es
    import numpy as np
except ImportError:
    raise ImportError("essentia and numpy are required only for import.py. Please install them if you want to use this module.")
logger = get_logger("music.import")
class Import:
    model_inst = None
    model_happy = None
    model_genre = None
    def __init__(self, source_type, source, output_path, genres=None):
        self.source_type = source_type  # 'youtube' or 'local'
        self.source = source  # list of URLs or directory path
        self.output_path = output_path
        self.genres = genres or []
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
                logger.error(f"An error occurred while downloading: {e}")
                return None
    def get_informations(self, link):
        with yt_dlp.YoutubeDL(self.opts) as ydl:
            try:
                info = ydl.extract_info(link, download=False)
                
                return info
            except Exception as e:
                logger.error(f"An error occurred while extracting information: {e}")
                return None
    def import_music(self):
        if self.source_type == 'youtube':
            for link in self.source:
                logger.info(f"➡️ Starting import for link: {link}")
                self.download_audio(link)
                info = self.get_informations(link)
                if not info:
                    logger.warning(f"Skipping link due to missing info: {link}")
                    continue
                analyse = self.analyse(os.path.join(self.output_path, f"{info['title']}.mp3"))
                logger.debug(f"Analyse result for {info['title']}: {analyse}")
                logger.info(f"Importing music from YouTube link: {link} -> {info.get('title')}")
                music = Music(os.path.join(self.output_path, f"{info['title']}.mp3"))
                music.insert_metadata(
                    genre=self.genres if self.genres else [analyse['genre']],
                    authors=info.get('creators', None) ,
                    mood=analyse['happy_mood_probability'] / 100.0, 
                    energy=analyse['energy'],
                    bpm=analyse['bpm'], 
                    danceability=analyse['danceability'], 
                    popularity=max(min(info.get('view_count', 0) / 1e9 , 0.0), 1.0) , 
                    instrumental=analyse['vocal_probability'] > 0.3, 
                    year=info.get('upload_date', "19000101")[:4],
                    copyright=False
                )
                self.db.insert_music(music)
        elif self.source_type == 'local':
            import shutil
            input_dir = self.source
            dest_dir = self.output_path if self.output_path else 'audio_files/'
            os.makedirs(dest_dir, exist_ok=True)
            files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith('.mp3') or f.endswith('.wav')]
            for file_path in files:
                filename = os.path.basename(file_path)
                dest_path = os.path.join(dest_dir, filename)
                if os.path.abspath(file_path) != os.path.abspath(dest_path):
                    shutil.copy2(file_path, dest_path)
                    logger.info(f"Copied {file_path} to {dest_path}")
                else:
                    logger.info(f"File {file_path} already in destination {dest_path}")
                logger.info(f"➡️ Starting import for local file: {dest_path}")
                analyse = self.analyse(dest_path)
                print(analyse)
                logger.debug(f"Analyse result for {os.path.basename(dest_path)}: {analyse}")
                music = Music(dest_path)
                music.insert_metadata(
                    genre=self.genres if self.genres else [analyse['genre']],
                    authors=None,
                    mood=analyse['happy_mood_probability'] / 100.0,
                    energy=analyse['energy'],
                    bpm=analyse['bpm'],
                    danceability=analyse['danceability'],
                    popularity=0.0,
                    instrumental=analyse['vocal_probability'] > 0.3,
                    year=None,
                    copyright=False
                )
                self.db.insert_music(music)
        else:
            logger.error("Unknown source type. Use 'youtube' or 'local'.")

    def analyse(self, path):
        logger.info(f"🎵 Analyse de {path} en cours...")
        audio_44k = es.MonoLoader(filename=path, sampleRate=44100)()
        audio_16k = es.MonoLoader(filename=path, sampleRate=16000)()
        logger.debug("⏳ Calcul du rythme et de l'énergie...")
        bpm, _, _, _, _ = es.RhythmExtractor2013(method="multifeature")(audio_44k)
        energy = es.Energy()(audio_44k)
        danceability, _ = es.Danceability()(audio_44k)

        logger.info(f"  👉 BPM : {bpm:.0f}")
        logger.info(f"  👉 Énergie globale : {energy:.4f}")
        logger.info(f"  👉 Danceability : {danceability:.4f} (plus c'est haut, plus c'est dansant)")

        logger.debug("🧠 Analyse IA en cours...")
        # Load models only once
        if Import.model_inst is None:
            Import.model_inst = es.TensorflowPredictMusiCNN(graphFilename="models/voice_instrumental-musicnn-msd-2.pb")
        if Import.model_happy is None:
            Import.model_happy = es.TensorflowPredictMusiCNN(graphFilename="models/mood_happy-musicnn-msd-2.pb")
        if Import.model_genre is None:
            Import.model_genre = es.TensorflowPredictMusiCNN(graphFilename="models/genre_rosamerica-musicnn-msd-2.pb")

        predictions_inst = Import.model_inst(audio_16k)
        moyenne_inst = np.mean(predictions_inst, axis=0)
        logger.info(f"  👉 Probabilité Instrumental : {moyenne_inst[0]:.1%}")
        logger.info(f"  👉 Probabilité Présence de Voix : {moyenne_inst[1]:.1%}")

        predictions_happy = Import.model_happy(audio_16k)
        moyenne_happy = np.mean(predictions_happy, axis=0)
        logger.info(f"  👉 Probabilité Mood Joyeux : {moyenne_happy[1]:.1%}")

        predictions_genre = Import.model_genre(audio_16k)
        moyenne_genre = np.mean(predictions_genre, axis=0)
        liste_genres = ['Classique', 'Hip Hop', 'Jazz', 'Pop', 'R&B', 'Rock', 'Voix parlée', 'Lo-Fi']
        index_dominant = np.argmax(moyenne_genre)
        genre_dominant = liste_genres[index_dominant]
        logger.info(f"  👉 Genre principal détecté : {genre_dominant} (avec {moyenne_genre[index_dominant]:.1%} de certitude)")
        return {
            "bpm": bpm,
            "energy": energy ,
            "danceability": danceability,
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
    parser.add_argument("--source_type", type=str, choices=['youtube', 'local'], required=True, help="Source type: 'youtube' for URLs, 'local' for files in input/")
    parser.add_argument("--source", type=str, nargs='+', required=True, help="List of YouTube URLs or path to input directory")
    parser.add_argument("--output", type=str, default="audio_files/", help="Path to save the music file with inserted metadata")
    parser.add_argument("--genres", type=str, nargs='*', help="Genres to assign to the music")
    args = parser.parse_args()
    Import(args.source_type, args.source if args.source_type == 'youtube' else args.source[0], args.output, genres=args.genres).import_music()