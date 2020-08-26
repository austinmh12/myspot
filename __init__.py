import logging
import json
import requests as r
from spotipy import Spotify as _Spotify
from spotipy.oauth2 import SpotifyClientCredentials as SCC
from spotipy.util import prompt_for_user_token as user_token
from spotipy.exceptions import SpotifyException
from .client_info import USER_ID, CLIENT_ID, CLIENT_SECRET

log = logging.getLogger(__name__)
fhandler = logging.FileHandler('/home/austinmh12/Documents/Code/Python/myspot.log')
fhandler.setFormatter(logging.Formatter('[%(asctime)s - %(name)s - %(levelname)s] %(message)s'))
shandler = logging.StreamHandler()
shandler.setFormatter(logging.Formatter('[%(asctime)s - %(name)s - %(levelname)s] %(message)s'))
log.addHandler(shandler)
log.addHandler(fhandler)
log.setLevel(logging.INFO)

CACHE_PATH = f'/home/austinmh12/Documents/Code/Python/.cache-{USER_ID}'

def get_token(client_id=CLIENT_ID, client_secret=CLIENT_SECRET):
	auth = SCC(client_id, client_secret)
	return auth.get_access_token()

def get_user_token(user_id=USER_ID, client_id=CLIENT_ID, client_secret=CLIENT_SECRET, cache_path=CACHE_PATH):
	return user_token(
		username=user_id,
		scope='playlist-modify-public user-read-recently-played',
		client_id=client_id,
		client_secret=client_secret,
		redirect_uri='http://localhost/',
		cache_path=cache_path
	)

def chunk(l, size):
	for i in range(0, len(l), size):
		yield l[i:i+size]

class Spotify(_Spotify):
	def __init__(self, token=None):
		if not token:
			token = get_user_token()
		super().__init__(auth=token)

	def get_playlist(self, playlist):
		playlists = self.current_user_playlists().get('items', [])
		if not playlists:
			return
		names = {p.get('name'): p for p in playlists}
		ret = names.get(playlist, None)
		if ret:
			return Playlist.from_dict(ret, spotify=self)
		ids = {p.get('id'): p for p in playlists}
		ret = ids.get(playlist, None)
		if ret:
			return Playlist.from_dict(ret, spotify=self)

	def get_history(self):
		return [Track.from_dict({**t['track'], **t}) for t in self.current_user_recently_played().get('items', [])]

	def track_search(self, q, type='track', limit=10):
		try:
			return [Track.from_dict(t) for t in self.search(q=q, type=type, limit=limit).get('tracks').get('items', [])][0]
		except IndexError:
			return

class Playlist:
	def __init__(self, name, id, description, uri, tracks, **kwargs):
		self.name = name
		self.id = id
		self.description = description
		self.uri = uri
		self.track_count = tracks.get('total', 0)
		self.collaborative = kwargs.get('collaborative', False)
		self.urls = kwargs.get('external_urls', {})
		self.href = kwargs.get('href', '')
		self.images = kwargs.get('images', [])
		self.owner = kwargs.get('owner', {})
		self.color = kwargs.get('color', None)
		self.public = kwargs.get('public', False)
		self.snapsnot_id = kwargs.get('snapshot_id', None)
		self.spotify = kwargs.get('spotify', Spotify())
		self.tracks = self.get_tracks()

	def get_tracks(self):
		tracks = []
		for i in range(0, self.track_count, 100):
			tracks.extend(self.spotify.playlist_tracks(self.id, offset=i).get('items', []))
		return [Track.from_dict(t['track']) for t in tracks]

	def add_tracks(self, tracks):
		tracks = [t for t in tracks if t not in self.tracks]
		log.info(f'Adding {len(tracks)} tracks to {self.name}.')
		for _tracks in chunk(tracks, 100):
			self.spotify.user_playlist_add_tracks(USER_ID, self.id, [t.id for t in _tracks])

	@classmethod
	def from_dict(cls, p_dict, spotify=None):
		return cls(spotify=spotify, **p_dict)

	def __str__(self):
		return f'{self.name} - {self.description}'

	def __eq__(self, p):
		return self.id == self.p

	def __repr__(self):
		return f'<myspot.Playlist({self.name})>'

class Track:
	def __init__(self, name, id, duration_ms, uri, **kwargs):
		self.name = name
		self.id = id
		self.duration = duration_ms
		self.uri = uri
		self.album = Album.from_dict(kwargs.get('album', {}))
		self.artists = [Artist.from_dict(a) for a in kwargs.get('artists', [])]
		self.disc_number = kwargs.get('disc_number', 0)
		self.explicit = kwargs.get('explicit', False)
		self.urls = kwargs.get('external_urls', {})
		self.href = kwargs.get('href', '')
		self.popularity = kwargs.get('popularity', 0)
		self.preview = kwargs.get('preview_url', None)
		self.track_number = kwargs.get('track_number', 0)
		self.played_at = kwargs.get('played_at', None)

	@classmethod
	def from_dict(cls, t_dict):
		return cls(**t_dict)

	def __str__(self):
		return f'{self.name} - {", ".join([a.name for a in self.artists])} - {self.album.name}'

	def __eq__(self, t):
		return self.id == t.id

	def __repr__(self):
		return f'<myspot.Track({self.name})>'

	def __hash__(self):
		return hash(self.id)

class Artist:
	def __init__(self, name, id, uri, **kwargs):
		self.name = name
		self.id = id
		self.uri = uri
		self.urls = kwargs.get('external_urls', {})
		self.href = kwargs.get('href', '')

	@classmethod
	def from_dict(cls, a_dict):
		return cls(**a_dict)

	def __str__(self):
		return f'{self.name}'

	def __eq__(self, a):
		return self.id == a.id

	def __repr__(self):
		return f'<myspot.Artist({self.name})>'

class Album:
	def __init__(self, name, id, uri, **kwargs):
		self.name = name
		self.id = id
		self.uri = uri
		self.artists = [Artist.from_dict(a) for a in kwargs.get('artists', [])]
		self.track_count = kwargs.get('total_tracks', 0)
		self.urls = kwargs.get('external_urls', {})
		self.href = kwargs.get('href', '')
		self.release_date = kwargs.get('release_date', '')
		self.images = kwargs.get('images', [])

	@classmethod
	def from_dict(cls, a_dict):
		return cls(**a_dict)

	def __str__(self):
		return f'{self.name} - {", ".join([a.name for a in self.artists])}'

	def __eq__(self, a):
		return self.id == self.a

	def __repr__(self):
		return f'<myspot.Album({self.name})>'