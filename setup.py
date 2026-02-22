from setuptools import setup, find_packages

setup(
    name="MusicPlaylistGenerator",
    version="0.1.0",
    description="A music playlist generator with audio analysis and metadata management.",
    author="Infuseting",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "essentia-tensorflow",
        "ffmpeg-python==0.2.0",
        "future==1.0.0",
        "mutagen==1.47.0",
        "yt-dlp==2026.2.4",
    ],
    entry_points={
        "console_scripts": [
            "music-playlist-generator=index:main"
        ]
    },
    python_requires=">=3.7",
)
