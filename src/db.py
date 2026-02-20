import sqlite3
from music import Music
from mutagen import MutagenError
import os


class DB:
    def __init__(self, path):
        self.db = sqlite3.connect(f"{path}/music_metadata.db")
        self.cursor = self.db.cursor()
        self.initialize()

    def initialize(self):
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
                                duration REAL,
                                bitrate INTEGER,
                                sample_rate INTEGER,
                                channels INTEGER,
                                mood TEXT,
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
        self.cursor.execute(
            """
                            INSERT OR IGNORE INTO music (path, duration, bitrate, sample_rate, channels, mood, energy, danceability, popularity, instrumental, year, copyright) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
            (
                music.path,
                music.duration,
                music.bitrate,
                music.sample_rate,
                music.channels,
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
        music_id = self.cursor.execute("SELECT id FROM music WHERE path = ?", (music.path,)).fetchone()[0]
        for genre in getattr(music, "genre", []):
            self.cursor.execute("""INSERT OR IGNORE INTO genres (name) VALUES (?)""", (genre,))
            self.db.commit()
            genre_id = self.cursor.execute(
                "SELECT id FROM genres WHERE name = ?", (genre,)
            ).fetchone()[0]
            self.cursor.execute(
                "INSERT OR IGNORE INTO has_genre (music_id, genre_id) VALUES (?, ?)",
                (music_id, genre_id),
            )
            self.db.commit()
        # authors (optional)
        for author in getattr(music, "authors", []):
            self.cursor.execute("INSERT OR IGNORE INTO authors (name) VALUES (?)", (author,))
            self.db.commit()
            author_id = self.cursor.execute("SELECT id FROM authors WHERE name = ?", (author,)).fetchone()[0]
            self.cursor.execute(
                "INSERT OR IGNORE INTO has_author (music_id, author_id) VALUES (?, ?)",
                (music_id, author_id),
            )
            self.db.commit()

    def remove_music(self, path):
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
        danceability=(0.0, 1.0),
        popularity=(0.0, 1.0),
        instrumental=False,
        year_range=(1900, 2100),
        copyright=False,
    ):
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
        if mood:
            where.append("m.mood = ?")
            params.append(mood)

        # numeric ranges
        where.append("m.energy BETWEEN ? AND ?")
        params.extend(list(energy))
        where.append("m.danceability BETWEEN ? AND ?")
        params.extend(list(danceability))
        where.append("m.popularity BETWEEN ? AND ?")
        params.extend(list(popularity))

        # instrumental
        where.append("(m.instrumental = ? OR ? = 0)")
        params.extend([instrumental, instrumental])

        # year range
        where.append("m.year BETWEEN ? AND ?")
        params.extend(list(year_range))

        # copyright logic per request:
        # - if copyright is True -> include both True and False (no filter)
        # - if copyright is False -> include only rows where copyright = 0
        if copyright:
            # no additional where clause
            pass
        else:
            where.append("m.copyright = 0")

        query = " ".join([base] + joins + ["WHERE"] + [" AND ".join(where)] + ["GROUP BY m.id"])
        self.cursor.execute(query, params)
        music_list = []
        for row in self.cursor.fetchall():
            try:
                music = Music(row[0])
                music.extract_metadata()
                music_list.append(music)
            except MutagenError as e:
                print(f"Error processing music file {row[0]}: {e}")
                try:
                    os.remove(row[0])
                except Exception as e:
                    print(f"Error deleting file {row[0]}: {e}")
                self.remove_music(row[0])
                self.db.commit()
        return music_list