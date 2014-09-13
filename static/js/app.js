window.App = Ember.Application.create({
    // Basic logging, e.g. "Transitioned into 'post'"
    //LOG_TRANSITIONS: true,

    // Extremely detailed logging, highlighting every internal
    // step made while transitioning into a route, including
    // `beforeModel`, `model`, and `afterModel` hooks, and
    // information about redirects and aborted transitions
    //LOG_TRANSITIONS_INTERNAL: true,

    //LOG_ACTIVE_GENERATION: true,
    //LOG_RESOLVER: true,
});

var inflector = Ember.Inflector.inflector;
inflector.uncountable('queue');

App.ApplicationAdapter = DS.RESTAdapter.extend({
    namespace: 'api/v1.0'
});

App.Router.map(function() {
    this.resource('music', function() {
        this.resource('artists', {path: '/'}, function() {
            this.resource('artist', {path: 'artists/:artist_id'});
            this.resource('album', {path: 'albums/:album_id'});
        });
    });
    this.route('add_url');
    this.resource('queue');
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
    date: DS.attr('string'),
    songs: DS.hasMany('song', {async:true})
});

App.Song = DS.Model.extend({
    artist: DS.belongsTo('artist'),
    album: DS.belongsTo('album'),
    name: DS.attr('string'),
    length: DS.attr('string'),
    uri: DS.attr('string'),
    playing: DS.attr('boolean'),
    queue: DS.hasMany('queue', {async:true})
});

App.Queue = DS.Model.extend({
    pos: DS.attr('number'),
    song: DS.belongsTo('song', {async:true}),
    played: DS.attr('boolean')
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
                var listeners = '?';
                if (data['listeners']) {
                    listeners = data['listeners']
                }
                controller.set('listeners', listeners);
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

App.QueueRoute = Ember.Route.extend({
    model: function(params) {
        return this.store.find('queue');
    }
});

App.ArtistsController = Ember.ArrayController.extend({
    sortProperties: ['name'],
    sortAscending: true,
});
