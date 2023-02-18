from typing import Optional, Union
from flask_ask.models import statement
from asksonic.utils.response import play_track_response, enqueue_track_response
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
    shuffled = 'shuffled' if shuffle_playlist else ''
    log('Play playlist {playlist}')
    tracks = subsonic.playlist_tracks(playlist, shuffle_playlist)
    if tracks:
        track = queue.reset(tracks)
        return play_track_response(
            track,
            render_template(
                'playing_playlist',
                playlist=playlist,
                shuffled=shuffled
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
    return find_song(title, artist, False)


@ask.intent('AskSonicQueueSongIntent')
def queue_song(title: str, artist: Optional[str]) -> Union[audio, statement]:
    return find_song(title, artist, True)


@ask.intent('AMAZON.YesIntent')
def yes_intent() -> Union[audio, statement]:
    songs = session.attributes['found_songs']
    queue_song = session.attributes['queue_song']
    action = 'Queue' if queue_song else 'Play'
    track = subsonic.get_track(songs[0])
    if queue_song:
        queue.prepend(track)
        return enqueue_track_response(
            track,
            render_template(
                'playing_song',
                title=track.title, artist=track.artist,
                action=action
            )
        )
    else:
        track = queue.reset([track])
        return play_track_response(
            track,
            render_template(
                'playing_song',
                title=track.title, artist=track.artist,
                action=action
            )
        )


@ask.intent('AMAZON.NoIntent')
def no_intent():
    songs = session.attributes['found_songs']
    queue_song = session.attributes['queue_song']
    action = 'Queue' if queue_song else 'Play'
    del songs[0]
    track = subsonic.get_track(songs[0])
    if len(songs) < 1:
        return statement('No more matches')
    return question(f'Do you want to {action.lower()} {track.title} by {track.artist}?')


def find_song(title: str, artist: Optional[str], queue_song: bool) -> Union[audio, statement]:
    action = 'Queue' if queue_song else 'Play'
    if title.find('"') != -1:
        title = title.split('"')[1]
    tracks = subsonic.get_songs(title, artist)
    log(f'{action} Song: {artist} - {title}')
    if tracks:
        tracks = tracks[:5]
        if len(tracks) < 2:
            if queue_song:
                queue.prepend(tracks[0])
                return enqueue_track_response(
                    tracks[0],
                    render_template(
                        'playing_song',
                        title=tracks[0].title, artist=tracks[0].artist,
                        action=action
                    )
                )
            else:
                track = queue.reset(tracks)
                return play_track_response(
                    track,
                    render_template(
                        'playing_song',
                        title=track.title, artist=track.artist,
                        action=action
                    )
                )
        session.attributes['found_songs'] = [t.id for t in tracks]
        session.attributes['queue_song'] = queue_song
        return question(f'I found multiple songs. Do you want to {action.lower()} {tracks[0].title} by {tracks[0].artist}?')
    return statement(
        render_template('song_not_found', song=title, artist=artist)
    )


def log(msg: str) -> None:
    logger.debug(msg)
