module('integration tests', {
    setup: function() {
        Ember.run(function() {
            App.reset();
        });
    },
    teardown: function() { }
});

//test('github commits pulls 5 commits', function() {
//    visit("/");
//    andThen(function() {
//        var rows = find("#github-commits > li").length;
//        equal(rows, 5);
//    });
//});
//
//test('adding song to queue will show up on queue page', function() {
//    visit("/music/artists");
//    andThen(function() {
//        click('#artist-list .list-group-item:first');
//    });
//    andThen(function() {
//        click('.album-link:first');
//    });
//    andThen(function() {
//        click('.queue-btn:first');
//    });
//    andThen(function() {
//        click('#nav-link-queue a');
//    });
//    andThen(function() {
//        var songs = find('.playlist-song').length;
//        equal(songs > 0, true);
//    });
//});

test('adding url to queue will fetch metadata for song', function() {
    visit("/add_url");
    andThen(function() {
        fillIn("#add-url-field", 'https://www.youtube.com/watch?v=OFbE3lHTcuo');
    });
    andThen(function() {
        click('#queue-btn');
        Ember.Test.registerWaiter(function () {
            var messages = $('#messages').html();
            if (messages) {
                return messages.endsWith('Song queued');
            }
            else {
                return false;
            }
        });
    });
    andThen(function() {
        visit('/playlists/current');
    });
    andThen(function() {
        var artist = find('.playlist-song:first > td:first').html()
        equal(artist, 'Fuck Buttons');
    });
});
