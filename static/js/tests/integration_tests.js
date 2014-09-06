App.setupForTesting();
App.injectTestHelpers();

module('integration tests', {
    setup: function() {
        Ember.run(function() {
            App.reset();
        });
    },
    teardown: function() { }
});

test('github commits pulls 5 commits', function() {
    visit("/");
    andThen(function() {
        var rows = find("#github-commits > li").length;
        equal(rows, 5);
    });
});

test('adding song to queue will show up on queue page', function() {
    visit("/music/artists");
    andThen(function() {
        click('#artist-list .list-group-item:first');
    });
    andThen(function() {
        click('.album-link:first');
    });
    andThen(function() {
        click('.queue-btn:first');
    });
    andThen(function() {
        click('#nav-link-queue a');
    });
    andThen(function() {
        var songs = find('.playlist-song').length;
        equal(songs > 0, true);
    });
});

//test('adding url to queue will fetch metadata for song', function() {
//    visit("/add_url");
//    andThen(function() {
//        fillIn("#add-url-field", 'https://www.youtube.com/watch?v=OFbE3lHTcuo');
//    });
//
//    var waiter;
//    waiter = function () {
//        var messages = $('#messages').html();
//        if (messages) {
//            if (messages.trim().endsWith('Song queued')) {
//                console.log('Song queued, continuing tests');
//                Ember.Test.unregisterWaiter(waiter);
//                return true;
//            }
//        }
//        else {
//            console.log('Song not queued, waiting');
//            return false;
//        }
//    };
//
//    andThen(function() {
//        click('#queue-btn');
//        Ember.Test.registerWaiter(waiter);
//        console.log('Waiting for song to queue');
//    });
//
//    andThen(function() {
//        console.log('Checking queue');
//        visit('/playlists/current');
//    });
//
//    andThen(function() {
//        var artist = find('.playlist-song:first > td:first').html()
//        equal(artist, 'Fuck Buttons');
//    });
//});
