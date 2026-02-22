import sqlite3
from music import Music
from mutagen import MutagenError
import os
from logging_config import get_logger

logger = get_logger("music.db")


class DB:
    def __init__(self, path):
        self.db = sqlite3.connect(f"{path}/music_metadata.db")
        self.cursor = self.db.cursor()
        self.initialize()

    def initialize(self):
        logger.debug("Initializing database schema if needed")
        self.cursor.execute(
            """
                            CREATE TABLE IF NOT EXISTS genres (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT UNIQUE
                            )
                            """
        )

        self.cursor.execute(
            """
                            CREATE TABLE IF NOT EXISTS has_genre (
                                music_id INTEGER,
                                genre_id INTEGER,
                                PRIMARY KEY (music_id, genre_id),
                                FOREIGN KEY (music_id) REFERENCES music(id),
                                FOREIGN KEY (genre_id) REFERENCES genres(id)
                            )
                            """
        )

        self.cursor.execute(
            """
                            CREATE TABLE IF NOT EXISTS authors (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT UNIQUE
                            )
                            """
        )

        self.cursor.execute(
            """
                            CREATE TABLE IF NOT EXISTS has_author (
                                music_id INTEGER,
                                author_id INTEGER,
                                PRIMARY KEY (music_id, author_id),
                                FOREIGN KEY (music_id) REFERENCES music(id),
                                FOREIGN KEY (author_id) REFERENCES authors(id)
                            )
                            """
        )

        self.cursor.execute(
            """
                            CREATE TABLE IF NOT EXISTS music (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                path TEXT UNIQUE,
                                md5 TEXT UNIQUE,
                                duration REAL,
                                bitrate INTEGER,
                                sample_rate INTEGER,
                                channels INTEGER,
                                bpm_moy REAL, 
                                mood REAL,
                                energy REAL,
                                
                                danceability REAL,
                                popularity REAL,
                                instrumental BOOLEAN,
                                year INTEGER,
                                copyright BOOLEAN
                            )
                            """
        )

    def insert_music(self, music: Music):
        import hashlib
        logger.info(f"➕ Inserting music into DB: {music.path}")
        # Compute md5 hash of the file
        try:
            with open(music.path, 'rb') as f:
                file_hash = hashlib.md5()
                while chunk := f.read(8192):
                    file_hash.update(chunk)
                md5sum = file_hash.hexdigest()
        except Exception as e:
            logger.error(f"Could not compute md5 for {music.path}: {e}")
            md5sum = None
        self.cursor.execute(
            """
                            INSERT OR IGNORE INTO music (path, md5, duration, bitrate, sample_rate, channels, bpm_moy, mood, energy, danceability, popularity, instrumental, year, copyright) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
            (
                music.path,
                md5sum,
                music.duration,
                music.bitrate,
                music.sample_rate,
                music.channels,
                music.bpm,
                music.mood,
                music.energy,
                music.danceability,
                music.popularity,
                music.instrumental,
                music.year,
                music.copyright,
            ),
        )
        self.db.commit()
        # ensure we have the music id (INSERT OR IGNORE may not set lastrowid)
        result = self.cursor.execute("SELECT id FROM music WHERE path = ?", (music.path,)).fetchone()
        if result is None:
            logger.warning(f"Music not inserted (duplicate or error): {music.path}")
            return
        music_id = result[0]
        logger.debug(f"Music id is {music_id}")
        for genre in getattr(music, "genre", []):
            self.cursor.execute("""INSERT OR IGNORE INTO genres (name) VALUES (?)""", (genre,))
            self.db.commit()
            genre_id = self.cursor.execute(
                "SELECT id FROM genres WHERE name = ?", (genre,)
            ).fetchone()[0]
            logger.debug(f"Linked genre '{genre}' (id={genre_id}) to music id {music_id}")
            self.cursor.execute(
                "INSERT OR IGNORE INTO has_genre (music_id, genre_id) VALUES (?, ?)",
                (music_id, genre_id),
            )
            self.db.commit()
        if music.authors:
            for author in music.authors:
                self.cursor.execute("INSERT OR IGNORE INTO authors (name) VALUES (?)", (author,))
                self.db.commit()
                author_id = self.cursor.execute("SELECT id FROM authors WHERE name = ?", (author,)).fetchone()[0]
                logger.debug(f"Linked author '{author}' (id={author_id}) to music id {music_id}")
                self.cursor.execute(
                    "INSERT OR IGNORE INTO has_author (music_id, author_id) VALUES (?, ?)",
                    (music_id, author_id),
                )
                self.db.commit()

    def remove_music(self, path):
        logger.info(f"🗑️ Removing music from DB: {path}")
        self.cursor.execute(
            "DELETE FROM has_genre WHERE music_id = (SELECT id FROM music WHERE path = ?)",
            (path,),
        )
        self.cursor.execute(
            "DELETE FROM has_author WHERE music_id = (SELECT id FROM music WHERE path = ?)",
            (path,),
        )
        self.cursor.execute("DELETE FROM music WHERE path = ?", (path,))
        self.db.commit()

    def query_music(
        self,
        genre=None,
        authors=None,
        mood="",
        energy=(0.0, 1.0),
        BPM=(0, 300),
        danceability=(0.0, 1.0),
        popularity=(0.0, 1.0),
        instrumental=False,
        year_range=(1900, 2100),
        copyright=False,
        sort_by="random"
    ):
        logger.info(f"🔎 Querying music with genre={genre} authors={authors} energy={energy} danceability={danceability} BPM={BPM} year_range={year_range}")
        # Build query dynamically to safely handle optional genre/author filters
        genre = genre or []
        authors = authors or []

        base = "SELECT m.path FROM music m"
        joins = []
        where = ["1=1"]
        params = []

        if genre:
            joins.append("JOIN has_genre hg ON m.id = hg.music_id")
            joins.append("JOIN genres g ON hg.genre_id = g.id")
            placeholders = ",".join("?" for _ in genre)
            where.append(f"g.name IN ({placeholders})")
            params.extend(genre)

        if authors:
            joins.append("JOIN has_author ha ON m.id = ha.music_id")
            joins.append("JOIN authors a ON ha.author_id = a.id")
            placeholders = ",".join("?" for _ in authors)
            where.append(f"a.name IN ({placeholders})")
            params.extend(authors)

        # mood (exact match) if provided
        if mood is not None:
            where.append("m.mood = ?")
            params.append(mood)

        # numeric ranges
        if energy is not None:
            where.append("m.energy BETWEEN ? AND ?")
            params.extend(list(energy))
        if danceability is not None:
            where.append("m.danceability BETWEEN ? AND ?")
            params.extend(list(danceability))
        if popularity is not None:
            where.append("m.popularity BETWEEN ? AND ?")
            params.extend(list(popularity))

        # instrumental
        if instrumental is not None:
            where.append("(m.instrumental = ? OR ? = 0)")
            params.extend([instrumental, instrumental])
        if BPM is not None:
            where.append("m.bpm_moy BETWEEN ? AND ?")
            params.extend(list(BPM))
        # year range
        if year_range is not None:
            where.append("m.year BETWEEN ? AND ?")
            params.extend(list(year_range))

        if copyright:
            pass
        else:
            where.append("m.copyright = 0")
        
        if sort_by == "popularity":
            order_clause = "ORDER BY m.popularity DESC"
        elif sort_by == "bpm":
            order_clause = "ORDER BY m.bpm_moy DESC"
        elif sort_by == "energy":
            order_clause = "ORDER BY m.energy DESC"
        elif sort_by == "danceability":
            order_clause = "ORDER BY m.danceability DESC"
        elif sort_by == "random":
            order_clause = "ORDER BY RANDOM()"



        query = " ".join([base] + joins + ["WHERE"] + [" AND ".join(where)] + ["GROUP BY m.id"] + [order_clause])
        logger.debug(f"SQL: {query} -- params={params}")
        self.cursor.execute(query, params)
        music_list = []
        for row in self.cursor.fetchall():
            try:
                music = Music(row[0])
                music.extract_metadata()
                music_list.append(music)
            except MutagenError as e:
                logger.error(f"Error processing music file {row[0]}: {e}")
                try:
                    os.remove(row[0])
                except Exception as e:
                    logger.error(f"Error deleting file {row[0]}: {e}")
                self.remove_music(row[0])
                self.db.commit()
        logger.info(f"✅ Query returned {len(music_list)} items")
        return music_list