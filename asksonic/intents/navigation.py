from typing import Optional, Union
from flask_ask.models import statement
from asksonic.utils.response import play_track_response
from flask.templating import render_template
from flask_ask import question, audio, session
from asksonic import ask, logger, tracks_count
from asksonic.utils.subsonic import subsonic
from . import queue


@ask.intent('AMAZON.HelpIntent')
@ask.launch
def launch() -> question:
    log('Launch')
    return question(render_template('launch_text')) \
        .simple_card(
            title=render_template('launch_title'),
            content=render_template('launch_content')
    )


@ask.intent('AskSonicShuffleLibraryIntent')
def play_random_tracks() -> audio:
    log('Shuffle Library')
    tracks = subsonic.random_tracks(tracks_count)
    track = queue.reset(tracks)
    return play_track_response(track, render_template('playing_library'))


@ask.intent('AskSonicShuffleGenreIntent')
def play_genre_tracks(genre: str) -> audio:
    log('Shuffle Genre')
    tracks = subsonic.random_tracks(tracks_count, genre)
    track = queue.reset(tracks)
    return play_track_response(track, render_template('playing_genre', genre=genre))


@ask.intent('AskSonicPlayArtistIntent')
def play_artist(artist: str) -> Union[audio, statement]:
    log(f'Play Artist: {artist}')
    tracks = subsonic.artist_tracks(artist, tracks_count)
    if tracks:
        track = queue.reset(tracks)
        return play_track_response(
            track,
            render_template('playing_artist', artist=track.artist)
        )
    return statement(render_template('artist_not_found', artist=artist))


@ask.intent('AskSonicPlayAlbumIntent')
def play_album(album: str, artist: Optional[str]) -> Union[audio, statement]:
    log(f'Play Album: {artist} - {album}')
    tracks = subsonic.album_tracks(album, artist)
    if tracks:
        track = queue.reset(tracks)
        return play_track_response(
            track,
            render_template(
                'playing_album',
                album=track.album, artist=track.artist
            )
        )
    return statement(
        render_template('album_not_found', album=album, artist=artist)
    )


@ask.intent('AskSonicPlayPlaylistIntent')
def play_playlist(mode: str, playlist: str) -> Union[audio, statement]:
    shuffle_playlist = True if (mode == 'shuffle') else False
    log('Play playlist {playlist}')
    tracks = subsonic.playlist_tracks(playlist, shuffle_playlist)
    if tracks:
        track = queue.reset(tracks)
        return play_track_response(
            track,
            render_template(
                'playing_playlist',
                playlist=playlist
            )
        )
    return statement(render_template('playlist_not_found', playlist=playlist))


@ask.intent('AskSonicListArtistAlbumsIntent')
def list_artist_albums(artist: str) -> Union[audio, statement]:
    log(f'List Artist Albums: {artist}')
    albums = subsonic.artist_albums(artist)
    if albums:
        album_titles = ', '.join([a['name'] for a in albums])
        return statement(
            render_template(
                'artist_albums',
                artist=artist, album_titles=album_titles
            )
        )
    return statement(
        render_template('artist_not_found', artist=artist)
    )


@ask.intent('AskSonicPlaySongIntent')
def play_song(title: str, artist: Optional[str]) -> Union[audio, statement]:
    if title.find('"') != -1:
        title = title.split('"')[1]
    log(f'Play Song: {artist} - {title}')
    tracks = subsonic.get_songs(title, artist)
    if tracks:
        tracks = tracks[:5]
        if len(tracks) < 2:
            track = queue.reset(tracks)
            return play_track_response(
                track,
                render_template(
                    'playing_song',
                    title=track.title, artist=track.artist
                )
            )
        session.attributes['found_songs'] = [t.id for t in tracks]
        return question(f'I found multiple songs. Do you want to hear {tracks[0].title} by {tracks[0].artist}?')
    return statement(
        render_template('song_not_found', song=title, artist=artist)
    )


@ask.intent('AMAZON.YesIntent')
def yes_intent() -> Union[audio, statement]:
    songs = session.attributes['found_songs']
    track = queue.reset([subsonic.get_track(songs[0])])
    return play_track_response(
        track,
        render_template(
            'playing_song',
            title=track.title, artist=track.artist
        )
    )


@ask.intent('AMAZON.NoIntent')
def no_intent():
    songs = session.attributes['found_songs']
    del songs[0]
    track = subsonic.get_track(songs[0])
    if len(songs) < 1:
        return statement('No more matches')
    return question(f'Do you want to hear {track.title} by {track.artist}?')


def log(msg: str) -> None:
    logger.debug(msg)
