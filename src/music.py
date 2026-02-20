from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TCON, COMM, TXXX, TPE1

class Music:
    def __init__(self, path):
        self.path = path
        # default metadata fields
        self.genre = []
        self.authors = []
        self.duration = None
        self.bitrate = None
        self.sample_rate = None
        self.channels = None
        self.mood = ""
        self.energy = 0.0
        self.danceability = 0.0
        self.popularity = 0.0
        self.instrumental = False
        self.year = 1900
        self.copyright = False
    def insert_metadata(self, genre=[], authors=[], mood="", energy=0.0, danceability=0.0, popularity=0.0, instrumental=False, year=1900, copyright=False):
        audio = MP3(self.path, ID3=ID3)
        if audio.tags is None:
            try:
                audio.add_tags()
            except TypeError:
                audio.add_tags(ID3=ID3)

        audio.tags.add(TCON(encoding=3, text=genre))
        
        if authors:
            audio.tags.add(TPE1(encoding=3, text=authors if isinstance(authors, list) else [authors]))
        audio.tags.add(TXXX(encoding=3, desc='Mood', text=mood))
        audio.tags.add(TXXX(encoding=3, desc='Energy', text=str(energy)))
        audio.tags.add(TXXX(encoding=3, desc='Danceability', text=str(danceability)))
        audio.tags.add(TXXX(encoding=3, desc='Popularity', text=str(popularity)))
        audio.tags.add(TXXX(encoding=3, desc='Instrumental', text=str(instrumental)))
        audio.tags.add(TXXX(encoding=3, desc='Year', text=str(year)))
        audio.tags.add(COMM(encoding=3, desc='Copyright', text=str(copyright)))  
        audio.save()
    def extract_metadata(self):
        audio = MP3(self.path, ID3=ID3)
        self.duration = audio.info.length
        self.bitrate = audio.info.bitrate
        self.sample_rate = audio.info.sample_rate
        self.channels = audio.info.channels
        self.genre = audio.tags.get('TCON', None).text if audio.tags.get('TCON', None) else []
        self.authors = audio.tags.get('TPE1', None).text if audio.tags.get('TPE1', None) else []
        self.mood = audio.tags.get('TXXX:Mood', None).text[0] if audio.tags.get('TXXX:Mood', None) else ""
        self.energy = float(audio.tags.get('TXXX:Energy', None).text[0]) if audio.tags.get('TXXX:Energy', None) else 0.0
        self.danceability = float(audio.tags.get('TXXX:Danceability', None).text[0]) if audio.tags.get('TXXX:Danceability', None) else 0.0
        self.popularity = float(audio.tags.get('TXXX:Popularity', None).text[0]) if audio.tags.get('TXXX:Popularity', None) else 0.0
        self.instrumental = audio.tags.get('TXXX:Instrumental', None).text[0].lower() == 'true' if audio.tags.get('TXXX:Instrumental', None) else False
        self.year = int(audio.tags.get('TXXX:Year', None).text[0]) if audio.tags.get('TXXX:Year', None) else 1900
        self.copyright = audio.tags.get('COMM:Copyright', None).text[0].lower() == 'true' if audio.tags.get('COMM:Copyright', None) else False

if __name__ == "__main__":
    music = Music("audio_files/sample.mp3")
    music.insert_metadata(genre=["pop", "rock"], mood="happy", energy=0.8, danceability=0.7, popularity=0.9, instrumental=False, year=2020, copyright=False, authors=["Patrique Pratique"])
    music.extract_metadata()
    print(f"Duration: {music.duration} seconds")
    print(f"Bitrate: {music.bitrate} bps")
    print(f"Sample Rate: {music.sample_rate} Hz")
    print(f"Channels: {music.channels}")
    print(f"Genre: {music.genre}")
    print(f"Authors: {music.authors}")
    print(f"Mood: {music.mood}")
    print(f"Energy: {music.energy}")
    print(f"Danceability: {music.danceability}")
    print(f"Popularity: {music.popularity}")
    print(f"Instrumental: {music.instrumental}")
    print(f"Year: {music.year}")
    print(f"Copyright: {music.copyright}")
                