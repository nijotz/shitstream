module('integration tests', {
    setup: function() {
        Ember.run(function() {
            App.reset();
        });
    },
    teardown: function() { }
});


test('github commits pulls 5 commits', function() {
    var json = $.ajax({
        url: '/static/js/tests/fixtures/github.json',
        async: false,
    });
    stubEndpoint('/', json);
    visit("/");
    andThen(function() {
        var rows = find("#github-commits > li").length;
        equal(rows, 5);
    });
});
