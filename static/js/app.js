window.App = Ember.Application.create({
    // Basic logging, e.g. "Transitioned into 'post'"
    LOG_TRANSITIONS: true, 

    // Extremely detailed logging, highlighting every internal
    // step made while transitioning into a route, including
    // `beforeModel`, `model`, and `afterModel` hooks, and
    // information about redirects and aborted transitions
    LOG_TRANSITIONS_INTERNAL: true
});

var inflector = Ember.Inflector.inflector;
inflector.uncountable('queue');

App.ApplicationAdapter = DS.RESTAdapter.extend({
    namespace: 'api/v1.0'
});

App.Router.map(function() {
    this.resource('music', function() {
        this.resource('artists', function() {
            this.resource('artist', {path: ':artist_id'}, function() {
            });
        });
        this.resource('albums', function() {
            this.resource('album', {path: ':album_id'});
        });
    });
    this.route('add_url');
    this.resource('playlists', function() {
        this.resource('playlist', {path: ':playlist_id'});
    });
});

App.LoadingView = Ember.View.extend({
    jquery: function() {
        function more_poop(poop) {
          poop.innerHTML += " 💩";
          setTimeout(function() { more_poop(poop); }, 100);
        }
        poop = document.getElementById('poop');
        more_poop(poop);
    }.on('didInsertElement')
});

App.LoadingRoute = Ember.Route.extend({});

App.Artist = DS.Model.extend({
    name: DS.attr('string'),
    albums: DS.hasMany('album', {async:true}),
    non_album_songs: DS.hasMany('song', {async:true})
});

App.Album = DS.Model.extend({
    name: DS.attr('string'),
    artist: DS.belongsTo('artist'),
    songs: DS.hasMany('song', {async:true})
});

App.Song = DS.Model.extend({
    artist: DS.belongsTo('artist'),
    album: DS.belongsTo('album'),
    title: DS.attr('string'),
    length: DS.attr('string'),
    file: DS.attr('string'),
    playing: DS.attr('boolean'),
    playlists: DS.hasMany('playlist_songs', {async:true})
});

App.Playlist = DS.Model.extend({
    songs: DS.hasMany('playlist_songs', {async:true}),
    current_song_pos: DS.attr('number')
})

App.PlaylistSong = DS.Model.extend({
    playlist: DS.belongsTo('playlist', {async:true}),
    pos: DS.attr('number'),
    song: DS.belongsTo('song', {async:true})
})

App.ArtistsView = Ember.View.extend({
    jquery: function() {
        $('#artist-list').
            affix({
                offset: {
                    top: $('#header').height()
                }
            }).
            height(
                $(window).height() - $('#header').height() - 50
            );
        $(window).resize(function() {
            $('#artist-list').height(
                //FIXME: copypasta from 2 lines up
                $(window).height() - $('#header').height() - 50
            );
        })
    }.on('didInsertElement')
});

App.ArtistsRoute = Ember.Route.extend({
    model: function(params) {
        return this.store.find('artist');
    }
});

App.ArtistRoute = Ember.Route.extend({
    model: function(params) {
        return this.store.find('artist', params.artist_id);
    }
});

App.ApplicationRoute = Ember.Route.extend({
    setupController: function(controller) {
        Ember.$.getJSON('/api/v1.0/listeners').
        then(function(data) {
            Ember.run(function() {
                controller.set('listeners', data['listeners']);
            });
        })
    }
});

App.IndexRoute = Ember.Route.extend({
    model: function() {
        return Ember.$.getJSON(
            'https://api.github.com/repos/nijotz/shitstream/commits'
        ).then(function(data) {
            return Ember.run(function() {
                return data.splice(0, 5);
            });
        })
    }
});

App.AddUrlRoute = Ember.Route.extend({
    actions: {
        queue_url: function(url) {

            $('#queue-btn').prop('disabled', true);
            var socket = io.connect('/api/v1.0/add_url/');

            socket.on('connect', function() {
                console.log('Sending URL: ' + url);
                socket.emit('add_url', {url: url});
            });

            socket.on('response', function(msg) {
                $('#messages').append(msg.msg + '\n');
                console.log('Received msg: ' + msg.msg);
            });

            socket.on('disconnect', function() {
                $('#queue-btn').prop('disabled', false);
            });
        }
    }
});

App.MusicRoute = Ember.Route.extend({
    actions: {
        queue_song: function(song) {
            $.getJSON(
                "/api/v1.0/playlists/current/queue_song/" + song.get('id'), //FIXME
                function(data) {
                    $('#alert-placeholder').append(
                        '<div class="alert alert-success alert-dismissible" role="alert">' +
                            '<button type="button" class="close" data-dismiss="alert">' +
                                '<span aria-hidden="true">&times;</span>' +
                                '<span class="sr-only">Close</span>' +
                            '</button>' +
                            'Song added to queue' +
                        '</div>'
                    )

                    var alertdiv = $('#alert-placeholder').children('.alert:last-child')
                    window.setTimeout(function() {
                        $(alertdiv).fadeTo(500, 0).slideUp(500, function(){
                            alertdiv.remove();
                        });
                    }, 3000);
                }
            );
        },
        queue_album: function(album) {
            $.getJSON(
                "/api/v1.0/playlists/current/queue_album/" + album.get('id'), //FIXME
                function(data) {
                    $('#alert-placeholder').append(
                        '<div class="alert alert-success alert-dismissible" role="alert">' +
                            '<button type="button" class="close" data-dismiss="alert">' +
                                '<span aria-hidden="true">&times;</span>' +
                                '<span class="sr-only">Close</span>' +
                            '</button>' +
                            'Album added to queue' +
                        '</div>'
                    )

                    var alertdiv = $('#alert-placeholder').children('.alert:last-child')
                    window.setTimeout(function() {
                        $(alertdiv).fadeTo(500, 0).slideUp(500, function(){
                            alertdiv.remove();
                        });
                    }, 3000);
                }
            );
        }
    }
});

App.AlbumRoute = Ember.Route.extend({
    model: function(params) {
        return this.store.find('album');
    }
});

App.SongRoute = Ember.Route.extend({
    model: function(params) {
        return this.store.find('song', params.song_id);
    }
});

App.PlaylistController = Ember.ObjectController.extend({
    filter_songs: function(future) {
        current_song_pos = this.get('model.current_song_pos');

        // Preserve 'this' through the Land of Promise Hell
        var self = this;

        // All this data is loaded async, so we need to return a new
        // PromiseArray to the template that will eventually contain the future
        // songs in the queue
        return DS.PromiseArray.create({
            promise: self.get('model.songs').then(function(songs) {
                songs = songs.filter(function(song) {
                    // If not playing, everything is part of the past queue
                    if (current_song_pos === null) { return !future; }

                    // FIXME: Holy shit, I'm soo tired and this logic can be
                    // simplified, I'm sure.
                    return ((song.get('pos') >= current_song_pos) && future) ||
                        ((song.get('pos') < current_song_pos) && !future);
                });

                if (!future) {
                    songs = songs.toArray().reverse();
                }

                return songs
            })
        });
    },

    future_songs: function() {
        return this.filter_songs(true);
    }.property('current_song_pos', 'songs'),

    past_songs: function() {
        return this.filter_songs(false);
    }.property('current_song_pos', 'songs')
})

App.PlaylistRoute = Ember.Route.extend({
    model: function(params) {
        return this.store.find('playlist', params.playlist_id);
    },
    actions: {
        'dequeue_song': function(playlist_song) {
            playlist_song.destroyRecord();
            /*
            $.getJSON(
                "/api/v1.0/playlists/current/dequeue_song/" + pos, //FIXME
                function(data) {
                    $('#alert-placeholder').append(
                        '<div class="alert alert-success alert-dismissible" role="alert">' +
                            '<button type="button" class="close" data-dismiss="alert">' +
                                '<span aria-hidden="true">&times;</span>' +
                                '<span class="sr-only">Close</span>' +
                            '</button>' +
                            'Song removed from queue' +
                        '</div>'
                    )

                    var alertdiv = $('#alert-placeholder').children('.alert:last-child')
                    window.setTimeout(function() {
                        $(alertdiv).fadeTo(500, 0).slideUp(500, function(){
                            alertdiv.remove();
                        });
                    }, 3000);
                }
            );
            */
        }
    }
});

App.ArtistsController = Ember.ArrayController.extend({
    sortProperties: ['name'],
    sortAscending: true,
});
