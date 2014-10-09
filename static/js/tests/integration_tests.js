App.setupForTesting();
App.injectTestHelpers();

function async_wait(func) {
    var waiter;
    waiter = function () {
        return false;
    }
    function finished() {
        Ember.Test.unregisterWaiter(waiter);
    }
    Ember.Test.registerWaiter(waiter);
    func(finished);
    andThen(function () {});
}

module('integration tests', {
    setup: function() {
        Ember.run(function() {
            App.reset();
        });

        // Wait on back end to reset
        async_wait(function(finished) {
            Ember.$.ajax({
                url: '/tests/reset',
                success: function() {
                    finished();
                }
            });
        })
    }
});

test('github commits pulls 5 commits', function() {
    visit("/");
    andThen(function() {
        var rows = find("#github-commits > li").length;
        equal(rows, 5);
    });
});

test('adding song to queue will show up on queue page', function() {
    visit("/music/");
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

test('adding url to queue will show up on queue page, with tags', function() {
    visit("/add_url");
    andThen(function() {
        fillIn("#add-url-field", 'https://www.youtube.com/watch?v=OFbE3lHTcuo');
    });

    var waiter;
    waiter = function () {
        var messages = $('#messages').html();
        if (messages) {
            if (messages.trim().match(/Done$/)) {
                Ember.Test.unregisterWaiter(waiter);
                console.log('Song queued. Continuing.');
                return true;
            }
        }
        else {
            return false;
        }
    };

    andThen(function() {
        click('#queue-btn');
        Ember.Test.registerWaiter(waiter);
        console.log('Waiting for song to queue');
    });

    andThen(function() {
        click('#nav-link-queue a');
    })

    andThen(function() {
        var artist = find(".playlist-song .song-artist:contains('Fuck Buttons')");
        equal(artist.length > 0, true);
        var title = find(".playlist-song .song-name:contains('Surf Solar')");
        equal(title.length > 0, true);
    })
});

test('view album with multiple artist tags', function() {
    visit("/music/");
    andThen(function() {
        click("#artist-list .list-group-item:contains('Octopus')");
    });
    andThen(function() {
        click(".album-link:contains('Avalanche')");
    });
    andThen(function() {
        var songs = find('.album-song').length;
        equal(songs > 0, true);
    });
});

test('queue album with multiple artist tags', function() {
    visit("/music/");
    andThen(function() {
        click("#artist-list .list-group-item:contains('Octopus')");
    });
    andThen(function() {
        var album_lnk = find(".album-list > td > .album-link:contains('Avalanche')");
        var queue_btn = $(album_lnk).parent().parent().find('button')[0];
        click(queue_btn);
    });
    andThen(function() {
        var alerts = find("#alert-placeholder .alert:contains('Album added to queue')").length;
        equal(alerts > 0, true);
    });
    andThen(function() {
        click('#nav-link-queue a');
    })
    andThen(function() {
        var queue = find(".playlist-song").length;
        equal(queue > 0, true);
    });
});

test('album queues in correct order', function() {
    function base_test(artist, album) {
        visit("/music/");
        andThen(function() {
            click("#artist-list .list-group-item:contains('" + artist + "')");
        });
        andThen(function() {
            var album_lnk = find(".album-list > td > .album-link:contains('" + album + "')");
            var queue_btn = $(album_lnk).parent().parent().find('button')[0];
            click(queue_btn);
        });
        andThen(function() {
            var alerts = find("#alert-placeholder .alert:contains('Album added to queue')").length;
            equal(alerts > 0, true);
        });
        andThen(function() {
            click('#nav-link-queue a');
        })
        andThen(function() {
            for (var i = 0; i < 5; i++) {
                var song = find(".playlist-song:eq(+" + i.toString() + ") .song-track")[0];
                var html = $(song).html();
                equal(html.indexOf((i + 1).toString()) > -1, true);
            }
        });
    }

    // Has 1, 2, 3, etc tracks tags
    base_test('alt-J', 'An Awesome Wave');

    // Has 1/7, 2/7, 3/7, etc tracks tags
    base_test('Atriarch', 'Ritual of Passing');
});
