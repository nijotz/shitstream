window.App = Ember.Application.create();

var inflector = Ember.Inflector.inflector;
inflector.uncountable('queue');

App.ApplicationAdapter = DS.RESTAdapter.extend({
    namespace: 'api/v1.0'
});

App.Router.map(function() {
    this.resource('music', function() {
        this.resource('artists', function() {
            this.resource('artist', {path: ':artist_id'});
        });
    });
    this.resource('queue');
});

App.Artist = DS.Model.extend({
    name: DS.attr('string'),
    albums: DS.hasMany('album'),
    non_album_songs: DS.hasMany('song')
});

App.Album = DS.Model.extend({
    name: DS.attr('string'),
    artist: DS.belongsTo('artist')
});

App.Song = DS.Model.extend({
    uri: DS.attr('string'),
    artist: DS.attr('string'),
    album: DS.attr('string'),
    title: DS.attr('string'),
    length: DS.attr('string'),
    playing: DS.attr('boolean'),
    artist: DS.belongsTo('artist'),
    album: DS.belongsTo('album'),
    queue: DS.belongsTo('queue')
});

App.Queue = DS.Model.extend({
    songs: DS.hasMany('song')
})

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

App.AlbumRoute = Ember.Route.extend({
    model: function(params) {
        return this.store.find('album');
    }
});

App.QueueRoute = Ember.Route.extend({
    model: function(params) {
        return this.store.find('queue');
    },
    setupController: function(controller, queue) {
        controller.set('model', queue.get('songs'));
    }
});

App.QueueController = Ember.ArrayController.extend();

App.SongsController = Ember.ArrayController.extend({
    sortProperties : ['uri'],
    sortAscending : true
});
