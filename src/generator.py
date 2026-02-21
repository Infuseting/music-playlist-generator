from db import DB
from music import Music
from playlist import Playlist
from logging_config import get_logger

logger = get_logger("music.generator")


class Generator:
    def __init__(self):
        pass

    def generate(self, input_path, output_path, time, genre, authors=None, bpm=None, mood=None, energy=(0.0,1.0), danceability=(0.0,1.0), crossfade=0, normalize=False, popularity=(0.0,1.0), sort_by='random', instrumental=False, year_range=(1900,2100), copyright=False, BPM=(0, 300)):
        logger.info(f"➡️ Generator.generate start: input={input_path} time={time}min genre={genre}")
        self.db = DB(input_path)
        self.playlist = Playlist()
        paths = self.db.query_music(genre=genre, authors=authors, mood=mood, energy=energy, danceability=danceability, popularity=popularity, instrumental=instrumental, year_range=year_range, copyright=copyright, BPM=BPM)
        logger.debug(f"Found {len(paths)} candidate songs")
        while self.playlist.total_duration() < time:
            if len(paths) == 0: 
                logger.warning("Not enough songs to fill the requested duration. Generated playlist may be shorter than requested.")
                break
            self.playlist.add_song(paths.pop())
            logger.debug(f"Added song, playlist duration now {self.playlist.total_duration():.2f} minutes")
        self.playlist.sort_by(sort_by)
        if len(self.playlist.songs) == 0:
            logger.warning("No songs found matching the criteria.")
            return
        logger.info(f"Exporting playlist to {output_path} (crossfade={crossfade}, normalize={normalize})")
        self.playlist.export(output_path, crossfade, normalize)
        logger.info("✅ Generator.generate finished")