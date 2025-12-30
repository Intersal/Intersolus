from pathlib import Path
from mutagen.flac import FLAC
from mutagen.wave import WAVE
from collections import defaultdict
import jinja2

MUSIC_ROOT = Path(__file__).parent / "Albums"
FILES_ROOT = Path(__file__).parent / "static/files"

def find_audio_files():
    return [
        p for p in MUSIC_ROOT.rglob("*")
        if p.suffix.lower() in (".flac", ".wav")
    ]

def get_tag(audio, *names, default="Unknown"):
    for name in names:
        for key in audio.keys():
            if key.lower() == name.lower():
                return audio[key][0]
    return default

def infer_from_path(path: Path):
    album = path.parent.name
    filename = path.stem
    parts = filename.split(" - ")
    artist = parts[0] if len(parts) > 0 else "Unknown Artist"
    title = parts[-1] if len(parts) > 1 else filename
    return album, artist, title

def read_metadata(path: Path):
    try:
        if path.suffix.lower() == ".flac":
            audio = FLAC(path)
        else:
            audio = WAVE(path)
    except Exception as e:
        print(f"Error reading metadata for {path}: {e}")
        inferred_album, inferred_artist, inferred_title = infer_from_path(path)
        return {
            "album": inferred_album,
            "artist": inferred_artist,
            "title": inferred_title,
            "path": str(path),
        }

    album = get_tag(audio, "album", default=None)
    artist = get_tag(audio, "albumartist", "artist", default=None)
    title = get_tag(audio, "title", default=None)

    if album is None or artist is None or title is None:
        inferred_album, inferred_artist, inferred_title = infer_from_path(path)
        album = album or inferred_album
        artist = artist or inferred_artist
        title = title or inferred_title

    return {
        "album": album,
        "artist": artist,
        "title": title,
        "path": str(path),
    }

def load_tracks():
    return [read_metadata(f) for f in find_audio_files()]

def build_albums():
    folder_to_tracks = defaultdict(list)
    for track in load_tracks():
        folder = Path(track["path"]).parent
        folder_to_tracks[folder].append(track)

    albums_dict = {}

    for folder, tracks in folder_to_tracks.items():
        cover_path = get_album_cover(folder)

        first_meta = read_metadata(Path(tracks[0]["path"]))
        album_name = first_meta["album"]
        artist_name = first_meta["artist"]

        key = (album_name, artist_name)

        albums_dict[key] = {
            "album": album_name,
            "artist": artist_name,
            "cover": cover_path,
            "tracks": []
        }

        for track in tracks:
            relative_path = Path(track["path"]).relative_to(MUSIC_ROOT)
            albums_dict[key]["tracks"].append({
                "title": track["title"],
                "path": str(relative_path).replace("\\", "/")
            })
    return list(albums_dict.values())

def first_track_in_album(album_folder: Path):
    audio_files = sorted([f for f in album_folder.iterdir() if f.suffix.lower() in (".flac", ".wav")])
    return audio_files[0] if audio_files else None

def get_album_cover(folder: Path):
    first_track = first_track_in_album(folder)
    
    if first_track and first_track.suffix.lower() == ".flac":
        audio = FLAC(first_track)
        if audio.pictures:
            pic = audio.pictures[0]
            cover_file = Path(__file__).parent / "static" / f"{folder.name}_cover.jpg"
            if not cover_file.exists():
                with open(cover_file, "wb") as f:
                    f.write(pic.data)
            
            return cover_file.name 
            
    placeholder = folder / "placeholder.png"
    if placeholder.exists():
        static_cover = Path(__file__).parent / "static" / f"{folder.name}_cover.png"
        if not static_cover.exists():
            from shutil import copyfile
            copyfile(placeholder, static_cover)

        return static_cover.name 
        
    return None

if __name__ == "__main__":
    template_dir = Path(__file__).parent / "templates"
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))
    template = env.get_template("index.html")
    
    albums = build_albums()
    
    rendered_html = template.render(albums=albums)
    
    output_file = Path(__file__).parent / "index.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(rendered_html)
    
    print(f"Static website generated at {output_file}")
