import argparse
import datetime
from generator import Generator
from logging_config import configure_logging, get_logger


logger = get_logger("music.generator")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Music Playlist Generator")
    parser.add_argument("--input", type=str, default="audio_files/", help="Path to the directory containing audio files")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--output", type=str, default=f"export/{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_playlist.mp3", help="Path to save the generated playlist")
    parser.add_argument("--time", type=int, default=60, help="Duration of the playlist in minutes (can be not exact it's a minimum)")
    parser.add_argument("--genre", type=str, nargs="+", default=None, help="List of genres to include in the playlist (if not set, all genres allowed)")
    parser.add_argument("--authors", type=str, nargs='+', default=None, help="List of authors to include (if not set, all authors allowed)")
    parser.add_argument("--bpm", type=int, nargs=2, default=None, help="Range of BPM (Beats Per Minute) for the songs in the playlist (if not set, all BPM allowed)")
    parser.add_argument("--mood", type=str, default=None, help="Mood of the playlist (e.g., happy, sad, energetic; if not set, all moods allowed)")
    parser.add_argument("--energy", type=float, nargs=2, default=None, help="Range of energy levels for the songs in the playlist (0-1, if not set, all allowed)")
    parser.add_argument("--danceability", type=float, nargs=2, default=None, help="Range of danceability for the songs in the playlist (0-1, if not set, all allowed)")        
    parser.add_argument("--crossfade", type=int, default=5, help="Duration of crossfade between songs in seconds")
    parser.add_argument("--normalize", type=bool, default=True, help="Whether to normalize the audio levels of the songs in the playlist")
    parser.add_argument("--popularity", type=float, nargs=2, default=None, help="Range of popularity for the songs in the playlist (0-1, if not set, all allowed)")
    parser.add_argument("--sort-by", type=str, default="random", choices=["random", "popularity", "bpm", "energy", "danceability"] ,  help="Attribute to sort the songs by (e.g., bpm, energy, danceability)")
    parser.add_argument("--instrumental", type=bool, default=None, help="Whether to include only instrumental songs in the playlist (if not set, both allowed)")
    parser.add_argument("--copyright", type=bool, default=None, help="Whether to include only songs without copyright in the playlist (if not set, both allowed)")
    parser.add_argument("--year-range", type=int, nargs=2, default=None, help="Range of release years for the songs in the playlist (if not set, all allowed)")
    args = parser.parse_args()
    configure_logging(args.debug)
    logger.info(f"🚀 Starting generator (debug={args.debug})")
    generator = Generator()
    generator.generate(
        input_path=args.input,
        output_path=args.output,
        time=args.time,
        genre=args.genre,
        authors=args.authors,
        bpm=args.bpm,
        mood=args.mood,
        energy=args.energy,
        danceability=args.danceability,
        crossfade=args.crossfade,
        normalize=args.normalize,
        popularity=args.popularity,
        sort_by=args.sort_by,
        instrumental=args.instrumental,
        year_range=args.year_range,
        copyright=args.copyright,
        BPM=args.bpm
    )
    logger.info("✅ Generation finished")
    