import ffmpeg
from music import Music
import random
from logging_config import get_logger

logger = get_logger("music.playlist")


class Playlist: 
    def __init__(self):
        self.songs = []

    def add_song(self, music: Music):
        self.songs.append(music)
        logger.debug(f"Added song to playlist: {music.path} (duration={music.duration})")

    def export(self, output_path, crossfade, normalize):
        logger.info(f"🟢 Exporting playlist to {output_path} (songs={len(self.songs)})")
        if not self.songs:
            logger.warning("Export called with empty playlist")
            return
        input_streams = [ffmpeg.input(song.path) for song in self.songs]
        audio_node = input_streams[0].audio
        for next_stream in input_streams[1:]:
            audio_node = ffmpeg.filter([audio_node, next_stream.audio], 'acrossfade', d=crossfade)
        if normalize:
            audio_node = audio_node.filter('loudnorm')
        sound = ffmpeg.output(audio_node, output_path)
        sound.run()
        logger.info("✅ Playlist exported")

    def total_duration(self):
        total = sum(song.duration / 60 for song in self.songs)
        logger.debug(f"Playlist total duration: {total}")
        return total

    def __str__(self):
        return "\n".join(f"{song.path} - {song.duration:.2f} seconds" for song in self.songs)

    def sort_by(self, attribute):
        logger.debug(f"Sorting playlist by {attribute}")
        if attribute == "random": random.shuffle(self.songs)
        else: self.songs.sort(key=lambda song: getattr(song, attribute, 0), reverse=True)