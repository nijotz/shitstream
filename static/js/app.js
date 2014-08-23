window.App = Ember.Application.create();

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
    this.resource('playlists', function() {
        this.resource('playlist', {path: ':playlist_id'});
    });
});

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
    playlists: DS.hasMany('playlist', {async:true})
});

App.Playlist = DS.Model.extend({
    songs: DS.hasMany('song', {async:true})
})

App.ArtistsRoute = Ember.Route.extend({
    model: function(params) {
        return this.store.find('artist');
    }
});

App.ArtistRoute = Ember.Route.extend({
    model: function(params) {
        return this.store.find('artist', params.artist_id);
    },
    actions: {
        queue: function(song) {
            $.getJSON(
                "/api/v1.0/playlists/current/queue/" + song.get('id'), //FIXME
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

App.PlaylistRoute = Ember.Route.extend({
    model: function(params) {
        return this.store.find('playlist', params.playlist_id);
    }
});

App.ArtistsController = Ember.ArrayController.extend({
    sortProperties: ['name'],
    sortAscending: true,
});
